#!/bin/bash

export AWS_REGION="us-east-1"
export AWS_PROFILE="personal"
# App to test
export AppTemplateName="api_gateway_app"
export AppName="apigateway"
export InstallTypes=("all" "onlyapp" "appcloudtrail" "appcloudtrails3bucket" "appcloudwatchmetrics")

for InstallType in "${InstallTypes[@]}"
do
    export CloudTrailLogsBucketName="${AppName}-${InstallType}-qwerty"
    export AccountAlias="testapi${InstallType}"

    if [[ "${InstallType}" == "all" ]]
    then
        export CreateCloudTrailBucket="Yes"
        export CreateCloudTrailLogSource="Yes"
        export CreateCloudWatchMetricsSource="Yes"
    elif [[ "${InstallType}" == "onlyapp" ]]
    then
        export CreateCloudTrailBucket="No"
        export CreateCloudTrailLogSource="No"
        export CreateCloudWatchMetricsSource="No"
    elif [[ "${InstallType}" == "appcloudtrail" ]]
    then
        export CreateCloudTrailBucket="No"
        export CloudTrailLogsBucketName="lambda-all-randmomstring"
        export CreateCloudTrailLogSource="Yes"
        export CreateCloudWatchMetricsSource="No"
    elif [[ "${InstallType}" == "appcloudtrails3bucket" ]]
    then
        export CreateCloudTrailBucket="Yes"
        export CreateCloudTrailLogSource="Yes"
        export CreateCloudWatchMetricsSource="No"
    elif [[ "${InstallType}" == "appcloudwatchmetrics" ]]
    then
        export CreateCloudTrailBucket="No"
        export CreateCloudTrailLogSource="No"
        export CreateCloudWatchMetricsSource="Yes"
    else
        echo "No Choice"
    fi

    # Export Sumo Properties
    export SumoAccessID=""
    export SumoAccessKey=""
    export SumoOrganizationId=""
    export SumoDeployment="us1"
    export RemoveSumoResourcesOnDeleteStack=true

    # Export Collector Name
    export CollectorName="AWS-Sourabh-Collector${AppName}-${InstallType}"

    # Export CloudTrail Logs Details
    export CloudTrailBucketPathExpression="*"
    export CloudTrailLogsSourceName="AWS-CloudTrail-${AppName}-${InstallType}-Source"
    export CloudTrailLogsSourceCategoryName="AWS/CloudTrail/${AppName}/${InstallType}/Logs"

    # Export CloudWatch Metrics Details
    export CloudWatchMetricsSourceName="AWS-CloudWatch-Metrics-${AppName}-${InstallType}-Source"
    export CloudWatchMetricsSourceCategoryName="AWS/CloudWatch/${AppName}/${InstallType}/Metrics"

    export template_file="${AppTemplateName}.template.yaml"

    aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ././../sam/${template_file} \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name "${AppName}-${InstallType}" \
    --parameter-overrides SumoDeployment="${SumoDeployment}" SumoAccessID="${SumoAccessID}" SumoAccessKey="${SumoAccessKey}" \
    SumoOrganizationId="${SumoOrganizationId}" RemoveSumoResourcesOnDeleteStack="${RemoveSumoResourcesOnDeleteStack}" \
    CollectorName="${CollectorName}" CloudTrailLogsBucketName="${CloudTrailLogsBucketName}" CloudTrailBucketPathExpression="${CloudTrailBucketPathExpression}" \
    CloudTrailLogsSourceName="${CloudTrailLogsSourceName}" CloudTrailLogsSourceCategoryName="${CloudTrailLogsSourceCategoryName}" \
    CloudWatchMetricsSourceName="${CloudWatchMetricsSourceName}" CloudWatchMetricsSourceCategoryName="${CloudWatchMetricsSourceCategoryName}" \
    CreateCloudTrailBucket="${CreateCloudTrailBucket}" CreateCloudTrailLogSource="${CreateCloudTrailLogSource}" CreateCloudWatchMetricsSource="${CreateCloudWatchMetricsSource}" \
    AccountAlias="${AccountAlias}"

done

echo "All Installation Complete for ${AppName}"
