import json
import os

from common.logger import get_logger
from common.processtestfile import FileReader
from common.report import GenerateReport
from common.utils import run_command


class Validate(object):
    CUSTOM_RULES_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "customrules")

    def __init__(self, test_data, logger=None, only_validate=True):
        self.test_data = test_data
        self.template_path = test_data["Global"]["TemplatePath"]

        self.logger = logger if logger else get_logger(__name__)
        if only_validate:
            all_warnings = self.validate()
            # Create Report based on the available warnings.
            GenerateReport(all_warnings, test_data, "Pre-Deployment", True, logger)

    """
    Validation will be performed in three steps
    1. CFN LINTER - It will test the template only for validation related to linting. Only warnings.
    2. CFN NAG - It will test the template along with parameters. Only warnings.
    3. Custom Sumo Logic Rules. Failures is does not pass any custom rule.
    """

    def validate(self):
        self.logger.info("Pre Deployment validation is in progress ..............")
        pre_deployment = {}

        lint_issues = CfnLint.validate(self.template_path, self.logger)
        if lint_issues:
            pre_deployment["CFN-LINT"] = lint_issues

        test_parameters = FileReader.create_parameter_for_each_test(self.test_data)
        nag_issues_all = []
        for test_name, values in test_parameters.items():
            parameters = values["parameters"]
            parameter_file_path = "/tmp/parameter.json"
            try:
                with open(parameter_file_path, 'w') as parameter:
                    data = {"Parameters": parameters}
                    json.dump(data, parameter)
                nag_issues = CfnNag.validate(self.template_path, test_name, self.logger, parameter_file_path,
                                             self.CUSTOM_RULES_FOLDER)
            finally:
                os.remove(parameter_file_path)
            if nag_issues:
                nag_issues_all.extend(nag_issues)

        if nag_issues_all:
            pre_deployment["CFN-NAG"] = nag_issues_all

        self.logger.debug("Pre Deployment validation is complete with all issues as - %s." % json.dumps(pre_deployment))
        self.logger.info("Pre Deployment validation is Complete.")
        return {"Pre-Deployment": pre_deployment}


class CfnLint:

    @staticmethod
    def validate(template_path, logger):
        logger.debug("CFN Lint for the template %s." % template_path)

        commands = ["cfn-lint", "-t", template_path, "-f", "json"]
        if logger.level == "DEBUG":
            commands.extend(["-D", "True"])
        elif logger.level == "INFO":
            commands.extend(["-I", "True"])
        logger.debug("Running command as %s" % ' '.join(commands))

        response = run_command(commands)
        validation_data = json.loads(response)
        logger.debug("CFN Lint for the template %s is complete with result as %s." % (template_path, validation_data))

        transformed_data = CfnLint.transform_validation_data(validation_data)
        logger.debug(
            "CFN Lint for the template %s is complete with Transformed Data as %s." % (template_path, validation_data))

        return transformed_data

    @staticmethod
    def transform_validation_data(validation_data):
        validations = []
        if validation_data:
            for validation in validation_data:
                validations.append({"Level": validation["Level"],
                                    "Location": [validation["Location"]["Start"]],
                                    "Message": validation["Rule"]["Id"] + " - " + validation["Message"]}
                                   )
        return validations


class CfnNag:

    @staticmethod
    def validate(template_path, test_name, logger, parameter_file, custom_rules_folder):
        logger.debug("CFN Nag for the template %s." % template_path)

        commands = ["cfn_nag", template_path, "-u", "json", "-r", custom_rules_folder, "-m", parameter_file]
        if logger.level == "DEBUG":
            commands.extend(["-d", "True"])
        logger.debug("Running command as %s" % ' '.join(commands))

        response = run_command(commands)
        validation_data = json.loads(response)
        logger.debug(
            "CFN NAG for the template %s is complete with result as %s." % (template_path, validation_data))

        transformed_data = CfnNag.transform_validation_data(validation_data, test_name)
        logger.debug(
            "CFN NAG for the template %s is complete with Transformed Data as %s." % (template_path, validation_data))

        return transformed_data

    @staticmethod
    def transform_validation_data(validation_data, test_name):
        validations = []
        if validation_data:
            for file_level in validation_data:
                for validation in file_level["file_results"]["violations"]:
                    validations.append({"Level": "Warning" if validation["type"] == "WARN" else "Error",
                                        "Location": CfnNag.transform_line_numbers(validation["line_numbers"]),
                                        "TestName": test_name if "custom" in validation["id"] else "",
                                        "Resources": validation["logical_resource_ids"],
                                        "Message": validation["id"] + " - " + validation["message"]}
                                       )
        return validations

    @staticmethod
    def transform_line_numbers(line_numbers):
        output = []
        for line_number in line_numbers:
            output.append({'LineNumber': line_number})
        return output
