require 'brakeman/checks/base_check'
require 'brakeman/processors/lib/processor_helper'
require 'set'

#Checks for user input in methods which open or manipulate files
class Brakeman::CheckSourceOrSink < Brakeman::BaseCheck
  Brakeman::Checks.add self

  @description = "Finds possible file read and send to internet"

  def findNodes(nodes, type)
    nodesMap = {}
    methodMap = {}
    nodes.each do |node|
      methods = get_methods(node)
      methods.each do |method|
        info = method[:location].to_s
        nodesMap[info] = [] if nodesMap[info].nil?
        nodesMap[info] << [node,method]
        methodMap[info] = method
      end
    end
    nodesMap.keys.each do |key|
      nodes = nodesMap[key]
      method = methodMap[key]
      #puts nodes
      setProtoSummary(nodes, method, type)
    end
  end


  def run_check
    Brakeman.debug "Finding possible file access"
	
    sources = getSources
    sinks = getSinks
    findNodes(sources, "src")
    findNodes(sinks, "sink")
    
    outputProtoSumarry
  end

end
