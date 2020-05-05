from common.logger import get_logger
from common.report import GenerateReport
from validator import predeployvalidation


class Validate(object):

    def __init__(self, test_data, delete_stack, logger=None):
        self.test_data = test_data
        self.template_path = test_data["Global"]["TemplatePath"]

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
        self.logger.info("Post Deployment validation is Complete.")
        return post_deployment

    def deploy_cf(self):
        self.logger.debug("Deploying the")
