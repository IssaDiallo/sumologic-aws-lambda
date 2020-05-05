import os

import jsonschema
from common.logger import get_logger
from common.utils import check_if_valid_file, get_absolute_path, load_json_file


class FileReader(object):
    RESOURCE_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "resources")

    def __init__(self, file_name, logger=None):
        self.file_full_path = os.path.realpath(file_name)
        self.logger = logger if logger else get_logger(__name__)
        self.test_schema = load_json_file(os.path.join(self.RESOURCE_FOLDER, "testfile.schema"))
        self.property_schema = load_json_file(os.path.join(self.RESOURCE_FOLDER, "parameterfile.schema"))

    def validate_file(self, json_data, schema):
        self.logger.debug("Validating the file with data as %s." % str(json_data))
        try:
            jsonschema.validate(json_data, schema)
            self.logger.debug("Validation complete for the file.")
            return True
        except jsonschema.ValidationError as e:
            raise Exception("Validation failed with validation error as %s." % str(e))

    def validate_paths_in_test_file(self, json_data):
        # Check if the template path is valid and is File.
        template_path = get_absolute_path(json_data.get("Global").get("TemplatePath"), self.file_full_path)
        check_if_valid_file(template_path)
        json_data.get("Global")["TemplatePath"] = template_path
        self.logger.debug("Provided Template path is %s" % template_path)

        # Check all parameters files in the test file.
        if "Tests" in json_data:
            for test in json_data.get("Tests"):
                if "Parameters" in test:
                    parameter_path = get_absolute_path(test.get("Parameters"), self.file_full_path)
                    check_if_valid_file(parameter_path)
                    self.validate_file(load_json_file(parameter_path), self.property_schema)
                    test["Parameters"] = parameter_path
                    self.logger.debug("Provided Parameter path is %s" % parameter_path)
        return True, json_data

    def process_test_file(self):
        """
        Read and validate the test JSON file. Validate Template and parameters JSON.
        Also, replace relative path with absolute path in the JSON object itself.
        """
        try:
            json_data = load_json_file(self.file_full_path)
            self.logger.debug("Reading of the file is complete.")
            if self.validate_file(json_data, self.test_schema):
                success, json_data = self.validate_paths_in_test_file(json_data)
                if success:
                    self.logger.info("Provided File is %s which passed all validation checks." % self.file_full_path)
                    return json_data
        except Exception as exception:
            self.logger.error(
                "Exception occurred while processing test file %s as %s." % (self.file_full_path, str(exception)))
            raise exception
        return None

    @staticmethod
    def create_parameter_for_each_test(json_data):
        processed_data = {}
        global_parameters = {}
        if "GlobalParameters" in json_data["Global"]:
            global_parameters = json_data["Global"]["GlobalParameters"]
        for test in json_data["Tests"]:
            if "Skip" not in test or not test["Skip"]:
                all_parameters = global_parameters
                parameter_path = test["Parameters"]
                parameters = load_json_file(parameter_path)
                all_parameters.update(parameters)

                assertions = []
                if "Assertions" in test:
                    assertions = test["Assertions"]

                processed_data[test["TestName"]] = {"parameters": all_parameters, "assertions": assertions}
        return processed_data
