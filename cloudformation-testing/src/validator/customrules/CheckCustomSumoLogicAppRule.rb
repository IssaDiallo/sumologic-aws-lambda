# frozen_string_literal: true

require 'cfn-nag/violation'
require 'cfn-nag/custom_rules/base'
require 'json'

class CheckCustomSumoLogicAppRule < BaseRule
  def rule_text
    'App Name Should not be empty in Custom Resource App.'
  end

  def rule_type
    Violation::FAILING_VIOLATION
  end

  def rule_id
    'Custom1'
  end

"""
Make this method generic for all custom resources to test conditions based input.
Helps user to test conditions without deploying the code.
"""
  def audit_impl(cfn_model)
    violating_apps = cfn_model.resources_by_type('Custom::App').select do |app|
        app.appName.nil? || app.appName.empty?
    end
    violating_apps.map(&:logical_resource_id)
  end

end