require 'brakeman/checks/base_check'
require 'brakeman/processors/lib/processor_helper'
require 'set'

#Checks for user input in methods which open or manipulate files
class Brakeman::CheckProtobuf < Brakeman::BaseCheck
  Brakeman::Checks.add self

  @description = "Finds possible file read and send to internet"

=begin
  def findDangerNodes(nodes)
    resultsSet = Set.new([])
    nodes.each do |node|
      methods = get_methods(node)
      methods.each do |method|
        info = method[:location].to_s
        next if resultsSet.include?(info)
        resultsSet << info
        setDanger(node, method)
      end
    end
  end
=end

  def run_check
    Brakeman.debug "Finding possible file access"
    #puts ">>>>>>>  ttt  "

    #t = tracker.find_call :method => :system, :nested => true
    #puts t.nil?
    #puts t
    


    resultsSet = Set.new([])
    sources = getSources
    sinks = getSinks
    #dangers = getDangers
    #findDangerNodes(dangers)
    
    sources.each do |source|#children
      source_methods = get_methods(source)
      sinks.each do |sink|#parent
        sink_methods = get_methods(sink)
        source_methods.each do |source_method|
          sink_methods.each do |sink_method|

            next if source_method == sink_method
            next if sink_method[:call].line < source_method[:call].line
            pnodes = Set.new([])  
            if tracker.isChildren(source_method, sink_method, pnodes)#|| tracker.isChildren(sink_method, source_method)
              #result_key = source_method[:location].to_s + " " + source_method[:call].line.to_s + " dst: " + sink_method[:location].to_s + " " + sink_method[:call].line.to_s
              result_key = Brakeman::OutputProcessor.new.format(source_method[:call]) + " " + Brakeman::OutputProcessor.new.format(sink_method[:call])
              next if resultsSet.include?(result_key)
              #process_result(source_method, sink_method)
              pnodes = pnodes.sort_by{|n| n[:call].line}
	   
              setProtoResult(source, sink, source_method, sink_method, pnodes)
              resultsSet << result_key
            end
          end
        end
      end
    end
    outputProtoResult
  end

  def process_result(fileRead,internetWrite)
    return unless original? internetWrite
    #puts fileRead
    #puts internetWrite
    message = msg("Potencial Malicious")

      warn :result => fileRead,
        :warning_type => "Read and Send",
        :warning_code => :file_access,
        :message => message,
        :confidence => :high,
        :code => internetWrite[:call],
        :user_input => ""

  end
end
