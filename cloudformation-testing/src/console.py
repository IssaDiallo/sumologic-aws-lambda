import argparse

from common import logger, processtestfile
from validator import predeployvalidation, postdeployvalidation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", '--test-type', dest='test_type', choices=["validate", "deploy"],
                        default="validate", help='Select the test type to perform on CF template.')

    parser.add_argument("-f", '--test-file', dest='test_file',
                        required=True, help='Provide the test file.')

    parser.add_argument("-d", '--debug-logging', dest='debug_logging', help='Provide to enable Debug Logging.')

    parser.add_argument("-r", '--delete-stack', dest='delete_stack',
                        help='Provide to delete the CloudFormation stacks created using post deployment testing.')

    args = parser.parse_args()

    # Enable Logger
    LOGGER = logger.get_logger(__name__, "DEBUG" if args.debug_logging else "INFO")

    # First Process the test File. Then pass the test file object for validation and deployment testing.
    file_reader = processtestfile.FileReader(args.test_file, LOGGER)
    json_data = file_reader.process_test_file()

    if args.test_type == "validate":
        predeployvalidation.Validate(json_data, LOGGER)
    if args.test_type == "deploy":
        postdeployvalidation.Validate(json_data, True if args.delete_stack else False, LOGGER)
    else:
        LOGGER.debug("%s provided is not valid test type." % args.test_type)


if __name__ == '__main__':
    main()
