import datetime
import json
import re
import time
from datetime import datetime

import boto3
import cfn_flip
from common.logger import get_logger
from common.utils import read_file
from tabulate import tabulate


class StackStatus:
    COMPLETE = ["CREATE_COMPLETE", "UPDATE_COMPLETE", "DELETE_COMPLETE"]
    IN_PROGRESS = [
        "CREATE_IN_PROGRESS",
        "DELETE_IN_PROGRESS",
        "UPDATE_IN_PROGRESS",
        "UPDATE_COMPLETE_CLEANUP_IN_PROGRESS",
    ]
    FAILED = [
        "DELETE_FAILED",
        "CREATE_FAILED",
        "ROLLBACK_IN_PROGRESS",
        "ROLLBACK_FAILED",
        "ROLLBACK_COMPLETE",
        "UPDATE_ROLLBACK_IN_PROGRESS",
        "UPDATE_ROLLBACK_FAILED",
        "UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS",
        "UPDATE_ROLLBACK_COMPLETE",
    ]


class Capabilities:
    IAM = "CAPABILITY_IAM"
    NAMED_IAM = "CAPABILITY_NAMED_IAM"
    AUTO_EXPAND = "CAPABILITY_AUTO_EXPAND"
    ALL = [IAM, NAMED_IAM, AUTO_EXPAND]


def criteria_matches(criteria: dict, instance):
    for k in criteria:
        if k not in instance.__dict__:
            raise ValueError("%s is not a valid property %s" % (k, type(instance)))
    for k, v in criteria.items():
        if getattr(instance, k) != v:
            return False
        elif k == "Timestamp" and getattr(instance, k) < v:
            return False
    return True


class FilterableList(list):
    def filter(self, criteria):
        if not criteria:
            return self
        f_list = FilterableList()
        for item in self:
            if criteria_matches(criteria, item):
                f_list.append(item)
        return f_list


class Stacks(FilterableList):
    pass


class Resources(FilterableList):
    pass


class Events(FilterableList):
    pass


class Stack(object):

    def __init__(self, test_name, parameters, region, template_path, logger, resource_names):
        self.parameters = self._generate_parameters(parameters)
        self.template_path = template_path
        self.logger = logger if logger else get_logger(__name__)
        self.resource_names = resource_names

        self.cf_client = boto3.client("cloudformation", region)
        self.stack_name = re.sub('[^A-Za-z0-9]+', '', test_name + "_" + region)
        self.region = region
        self.events = Events()
        self.resources = Resources()
        self.children = Stacks()
        self._last_event_refresh = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")

    def deploy_template(self):
        deployment_error = []
        try:
            # -- Check if this stack name already exists
            lo_stack_list = self.cf_client.describe_stacks()["Stacks"]
            ll_stack_exists = False
            for lo_stack in lo_stack_list:
                if self.stack_name == lo_stack["StackName"]:
                    self.logger.info("Stack Name %s already exist in Region %s" % (self.stack_name, self.region))
                    ll_stack_exists = True

            # -- If the stack already exists then delete it first
            if ll_stack_exists:
                self.logger.info("As Stack %s Already Exist, Deleting the Stack First." % self.stack_name)
                self.delete_stack()

            # -- Create Stack
            output_file = cfn_flip.to_json(read_file(self.template_path))
            self.cf_client.create_stack(StackName=self.stack_name,
                                        TemplateBody=output_file,
                                        Parameters=self.parameters,
                                        Capabilities=Capabilities.ALL)

            current_status = self._check_status()
            if current_status in StackStatus.FAILED:
                self.logger.info("Stack %s Creation Failed with Status as %s." % (self.stack_name, current_status))
                status = "FAIL"
                failed_resources = self.fetch_resources().filter({"ResourceStatus": "DELETE_FAILED"})
                for resource in failed_resources:
                    deployment_error.append({"Level": "Error", "Resources": resource["LogicalResourceId"],
                                             "Message": resource["ResourceStatusReason"]})
            else:
                self.logger.info("Stack %s Creation Complete." % self.stack_name)
                # Check all resource validation for the stack
                created_resources = self.fetch_resources()
                status = "PASS"
                for resource in created_resources:
                    extra_resources = []
                    if resource["LogicalResourceId"] not in self.resource_names:
                        extra_resources.append(resource["LogicalResourceId"])

                    if extra_resources:
                        deployment_error.append({"Level": "Error", "Resources": extra_resources,
                                                 "Message": "Extra Resource Created as "
                                                            "per the assertions provided in the CF Stack."})
                        status = "FAIL"
        except Exception as e:
            status = "FAIL"
            deployment_error = [{"Level": "Error", "Message": str(e)}]
        return status, deployment_error

    @staticmethod
    def _generate_parameters(parameters):
        stack_parameters = []
        if parameters:
            for parameter_name, parameter_value in parameters.items():
                stack_parameters.append({"ParameterKey": parameter_name, "ParameterValue": parameter_value})
        return stack_parameters

    def _check_status(self):
        stacks = self.cf_client.describe_stacks(StackName=self.stack_name)["Stacks"]
        current_stack = stacks[0]
        current_status = current_stack["StackStatus"]
        for ln_loop in range(1, 9999):
            self.logger.debug("Inside the loop with count as %s" % ln_loop)
            if current_status in StackStatus.IN_PROGRESS:
                time.sleep(20)
                try:
                    stacks = self.cf_client.describe_stacks(StackName=self.stack_name)["Stacks"]
                    self._print_stack_events(self.fetch_events())
                except Exception as e:
                    current_status = "STACK_DELETED"
                    break

                current_stack = stacks[0]
                if current_stack["StackStatus"] != current_stack:
                    current_status = current_stack["StackStatus"]
            else:
                self._print_stack_events(self.fetch_events())
                break
        return current_status

    def delete_stack(self):
        current_status = self._check_status()
        self.logger.info("Starting Stack %s deletion with current status as %s" % (self.stack_name, current_status))
        while current_status != "STACK_DELETED":
            if current_status == "DELETE_FAILED":
                failed_resources = self.fetch_resources().filter({"ResourceStatus": "DELETE_FAILED"})
                self.logger.info("Retain Resources %s and delete the stack %s again." % (
                    ', '.join(failed_resources), self.stack_name))
                self.cf_client.delete_stack(StackName=self.stack_name, RetainResources=failed_resources)
            else:
                self.cf_client.delete_stack(StackName=self.stack_name)
            current_status = self._check_status()
        self.logger.info("Complete Stack %s deletion with current status as STACK_DELETED" % self.stack_name)
        return "STACK_DELETED"

    def fetch_resources(self):
        resources = Resources()
        for page in self.cf_client.get_paginator("list_stack_resources").paginate(StackName=self.stack_name):
            for resource in page["StackResourceSummaries"]:
                resources.append(resource)
        self.resources = resources
        return self.resources

    def fetch_events(self):
        self._last_event_refresh = datetime.now()
        events = Events()
        for page in self.cf_client.get_paginator("describe_stack_events").paginate(StackName=self.stack_name):
            for event in page["StackEvents"]:
                events.append(event)
        self.events = events
        self._last_event_refresh = datetime.now()
        return self.events

    def _print_stack_events(self, events):
        self.logger.info(
            "********** Events -> Stack Name -> %s, Region -> %s **********" % (self.stack_name, self.region))
        headers = ['Timestamp', 'Resource Name', 'Resource Type', 'Resource Status', 'Resource Status Reason']
        rows = []
        for event in events:
            rows.append([event['Timestamp'], event['LogicalResourceId'], event['ResourceType'], event['ResourceStatus'],
                         event['ResourceStatusReason'] if "ResourceStatusReason" in event else ""])

        self.logger.info("\n" + tabulate(rows, headers=headers, tablefmt='orgtbl') + "\n")

        self.logger.info("************************** Events End **************************")
