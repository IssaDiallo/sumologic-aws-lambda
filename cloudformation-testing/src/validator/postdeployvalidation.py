import json
from concurrent import futures

import cfn_flip
from common.logger import get_logger
from common.processtestfile import FileReader
from common.report import GenerateReport
from common.utils import read_file
from validator import predeployvalidation
from common.CloudFormationUtility import Stack


class Validate(object):

    def __init__(self, test_data, delete_stack, logger=None):
        self.test_data = test_data
        self.template_path = test_data["Global"]["TemplatePath"]
        self.delete_stack = delete_stack
        self.logger = logger if logger else get_logger(__name__)

        # First Perform pre-Deployment Validation
        pre_deploy = predeployvalidation.Validate(test_data, logger, False)
        validations = pre_deploy.validate()
        pre_report = GenerateReport(validations, test_data, "Pre-Deployment", False, logger)
        if pre_report.report["Status"] == "PASS":
            # Perform Post Deployment validation
            post_validation = self.validate()
            validations["Post-Deployment"] = post_validation

            # Create Report based on the available warnings.
            GenerateReport(validations, test_data, "Post-Deployment", logger)

    """
    Perform post deployment validations. It will performed as below
    - Create the parameters to deploy the template
    - Deploy the template along with parameters using deploy with s3 bucket.
    - Validate all test cases
     - Check if only Assertions resources are created after deploy
     - Check all the assert conditions provided as passed
    - Delete the CF stack
    
    """

    # TODO: 'Test for flow testing - provide a mechanism to perform flow testing using external script.'
    def validate(self):
        self.logger.info("Post Deployment validation is in progress ..............")
        post_deployment = {}
        all_futures = {}
        test_parameters = FileReader.create_parameter_for_each_test(self.test_data)
        with futures.ThreadPoolExecutor(max_workers=2) as executor:
            results = {executor.submit(self.validate_each_test_case, test_name, test_data): (test_name, test_data)
                       for test_name, test_data in test_parameters.items()}
            all_futures.update(results)
            for future in futures.as_completed(all_futures):
                test_name, test_data = all_futures[future]
                test_name = str(test_name)
                try:
                    status, validation_result = future.result()
                    if status == "FAIL":
                        post_deployment[test_name] = validation_result
                except Exception as exc:
                    self.logger.info(
                        "Post Deployment - Test Case : %s failed with exception as: %s." % (test_name, exc))
                else:
                    self.logger.info("Post Deployment - Test Case: %s status is %s." % (test_name, status))
        self.logger.info("Post Deployment validation is Complete.")
        return post_deployment

    def validate_each_test_case(self, test_name, test_data):
        # Get the Object for CloudFormation
        # TODO: Make threading for regions
        for region in test_data["regions"]:
            cfn = Stack(test_name, test_data["parameters"], region, self.template_path, self.logger,
                        [assertion['ResourceName'] for assertion in test_data["assertions"] if 'ResourceName' in assertion])
            try:
                self.logger.debug("Starting with Test Case %s Validation with Data as %s." % (test_name, test_data))
                total_validation_errors = []

                # Parameter Validation Errors
                parameters_validation_errors = self._validate_parameters_provided(test_data["parameters"])
                if parameters_validation_errors:
                    total_validation_errors.extend(parameters_validation_errors)
                else:
                    status, deployment_errors = cfn.deploy_template()
                    if deployment_errors:
                        total_validation_errors.extend(deployment_errors)
                    else:
                        self.logger.info("CloudFormation Deployment complete for Test Case %s" % test_name)
                status = "FAIL" if len(total_validation_errors) > 0 else "PASS"
            except Exception as e:
                status = "FAIL"
                total_validation_errors = [{"Level": "Error", "Message": str(e)}]
            finally:
                # Delete Stacks properly
                cfn.delete_stack()
            return status, total_validation_errors

    def _validate_parameters_provided(self, assert_parameters):
        # Always convert to JSON irrespective of input as JSON or YAML.
        output_file = cfn_flip.to_json(read_file(self.template_path))
        json_data = json.loads(output_file)
        validation_errors = []
        if "Parameters" in json_data:
            all_parameters = json_data["Parameters"]
            for parameter_name, parameter_value in assert_parameters.items():
                if parameter_name not in all_parameters:
                    validation_errors.append({"Level": "Error",
                                              "Message": "Provided Test Parameter %s is not present "
                                                         "in the CloudFormation Template parameters." % parameter_name})

        return validation_errors
