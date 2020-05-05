import json

from common.logger import get_logger


class GenerateReport(object):

    def __init__(self, data, test_json, testing_type, generate_report, logger=None):
        self.data = data
        self.test_json = test_json
        self.testing_type = testing_type
        self.logger = logger if logger else get_logger(__name__)
        self.generate_report = generate_report
        self.report = {}
        self._generate_report()

    def _generate_report(self):

        cfn_nag = {"Error": 0, "Warning": 0}
        cfn_lint = {"Error": 0, "Warning": 0}
        post_deployment = {"Error": 0, "Warning": 0}
        test_cases = {}
        skipped_cases = 0

        for test in self.test_json["Tests"]:
            if "Skip" in test and test["Skip"]:
                skipped_cases = skipped_cases + 1
            else:
                test_cases[test["TestName"]] = "PASS"

        if self.data:
            for deployment_type, result in self.data.items():
                for issue_type, issues in result.items():
                    if issue_type == "CFN-NAG":
                        for issue in issues:
                            self._update_count(issue["Level"], cfn_nag)
                            if "TestName" in issue and issue["TestName"]:
                                test_cases[issue["TestName"]] = "FAIL"
                    elif issue_type == "CFN-LINT":
                        for issue in issues:
                            self._update_count(issue["Level"], cfn_lint)
                    else:
                        test_cases[issue_type] = "FAIL"
                        for test_case_details in issues:
                            self._update_count(test_case_details["Level"], post_deployment)

        failed_cases = sum(status == "FAIL" for status in test_cases.values())
        passed_cases = sum(status == "PASS" for status in test_cases.values())

        total = passed_cases + failed_cases + skipped_cases
        if total != len(self.test_json["Tests"]):
            raise Exception(
                "Issue with Report Generation as Total Test cases(%s) "
                "does not match Passed(%s) + Failed(%s)+ Skipped(%s) Test Cases" % (
                    total, passed_cases, failed_cases, skipped_cases))

        # Creating report data
        self.report = {"Template": self.test_json["Global"]["TemplatePath"], "Type": self.testing_type,
                       "Status": "FAIL" if failed_cases > 0 else "PASS",
                       "Total": total, "Pass": passed_cases, "Fail": failed_cases, "Skipped": skipped_cases,
                       "PreDeploymentIssues": [{"Cfn-Nag": cfn_nag}, {"Cfn-Lint": cfn_lint}],
                       "PostDeploymentIssues": post_deployment, "TestCases": test_cases}

        if self.generate_report:
            self.logger.info(
                "Report for %s CloudFormation Testing is : \n %s" % (
                    self.testing_type, json.dumps(self.report, indent=4)))

            # Create Result file
            with open("result.json", 'w') as parameter:
                json.dump(self.data, parameter, indent=4)

    @staticmethod
    def _update_count(level, dictionary_value):
        if level == "Error":
            dictionary_value["Error"] = dictionary_value["Error"] + 1
        elif level == "Warning":
            dictionary_value["Warning"] = dictionary_value["Warning"] + 1
