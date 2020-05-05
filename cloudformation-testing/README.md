# Sumo Logic AWS CloudFormation Testing Framework

The framework can be used to test the CloudFormation templates for Linting and CF best practices.

The framework can be used to test the custom Sumo Logic resources created using sumologic-app-utils package.

## Installation

Framework can be installed as a python package using `pip install `

###### Uses
 
## Test File

## Pre Deployment Testing

For Pre Deployment testing (Validation done on CF template before deploying it on AWS), we use below third party packages.

###### [CFN PYTHON LINT](https://github.com/aws-cloudformation/cfn-python-lint)
- Install the dependency using `pip install cfn-lint`.
- Helps to perform some basic validation on CF template to check the resources, mapping, parameters.
- It also checks for conditional dependencies within CF templates.
- For more details on all rules, try running `cfn-lint -l` after installing dependency.

###### [CFN NAG](https://github.com/stelligent/cfn_nag)
- The dependency require ruby to installed on the machine.
- The dependency can be installed using `gem install cfn-nag`
- Helps to check basic rules like S3 Bucket policy, Wild cards checks etc.

###### Custom Rules: We have some custom validation rules that checks for custom resource validation.
- Rule 1 : 

## Post Deployment Testing

## Report Generation

A report will be generated for each test file with the status of the test cases within the test files. Below is the format for the a report generated.

