# frozen_string_literal: true

require 'cfn-nag/violation'
require 'cfn-nag/custom_rules/base'
require 'json'

class TestRule < BaseRule
  def rule_text
    'asdkbalsbvlbdsjlvbljsbldvjdslcvjsv.'
  end

  def rule_type
    Violation::FAILING_VIOLATION
  end

  def rule_id
    'Custom2'
  end

    """
    Make this method generic for all custom resources to test conditions based input.
    Helps user to test conditions without deploying the code.
    """
  def audit_impl(cfn_model)
    violations = []
    logical_resource_ids = []

    data = File.read("/tmp/assertion.json")
    assertion_data = JSON.parse(data)

    assertion_data.each do |assert_resource|
        assert_resource_name = assert_resource["ResourceName"]
        cfn_resource = cfn_model.resource_by_id(assert_resource_name)
        if cfn_resource
            cfn_resource_name = cfn_resource.logical_resource_id
            if cfn_resource.resource_type == assert_resource["ResourceType"]
                if assert_resource["Assert"]
                    assert_resource["Assert"].each do |key, value|
                        if key and value.kind_of?(String)
                            violations << message_assert_failure(cfn_resource_name, value, cfn_resource.appSources, key)
                        end
                    end
                end
            else
                violations << message_assert_failure(cfn_resource_name, assert_resource["ResourceType"], cfn_resource.resource_type, "Resource Type")
            end
        else
            violations << message_resource_mismatch(assert_resource_name)
        end
    end

    if !violations.empty?
        File.open("/tmp/app.json","w") do |f|
          f.write(violations.to_json)
        end
        logical_resource_ids = violations.map{|x| x["Resource"]}
    end

    logical_resource_ids
  end

  def message_assert_failure(resource, assert_value, original_value, property)
    message = {
        "Resource" => resource,
        "Message" => "App - %s - Assert value %s does not match the CF value %s for property %s." % [resource, assert_value, original_value, property]
     }
  end

  def message_resource_mismatch(resource)
    message = {
        "Resource" => resource,
        "Message" => "App - %s - Resource %ss provided in Assertions does not match any resource in Cloud Formation template." % [resource, resource]
     }
  end

end