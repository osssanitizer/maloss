require 'brakeman/checks/base_check'
require 'brakeman/processors/lib/processor_helper'

#Checks for user input in methods which open or manipulate files
class Brakeman::CheckLocalExecute< Brakeman::BaseCheck
  Brakeman::Checks.add self

  @description = "Finds possible file read and send to internet"

  def run_check
    Brakeman.debug "Finding possible file access"
    methods = tracker.find_call :targets => [:IO, :Open3, :Kernel, :'POSIX::Spawn', :Process, nil],
      :methods => [:capture2, :capture2e, :capture3, :exec, :pipeline, :pipeline_r,
        :pipeline_rw, :pipeline_start, :pipeline_w, :popen, :popen2, :popen2e,
        :popen3, :spawn, :syscall, :system], :nested => true

    methods.concat tracker.find_call(:target => nil, :method => :`)


    targetList = [:Kernel, :Process, :Binding, :Open3, nil]
    methodList = [:[],:trap,:untrace_var,:lambda,:load,:fork,:eval,:builtin_xstring,]
    methods.concat tracker.find_call :targets => targetList, :methods => methodList
    methods.concat tracker.find_call :targets=>[:Process]
    methods.concat tracker.find_call :targets=>[:"Process.new"]
    

    methods.each do |method|
      process_result(method)
      end
  end

  def process_result(method)
    return unless original? method
    #puts fileRead
    #puts internetWrite
    message = msg("Local Execute")

      warn :result => method,
        :warning_type => "Local Execute",
        :warning_code => :file_access,
        :message => message,
        :confidence => :high,
        :code => method[:call],
        :user_input => ""

  end


end
