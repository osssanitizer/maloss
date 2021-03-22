require 'brakeman/checks/base_check'
require 'brakeman/processors/lib/processor_helper'

#Checks for user input in methods which open or manipulate files
class Brakeman::CheckRead < Brakeman::BaseCheck
  Brakeman::Checks.add self

  @description = "Finds possible file read and send to internet"

  def run_check
    Brakeman.debug "Finding possible file access"
    readTargetList = [:IO, :File, :FileUtils, :Kernel, :Open3]
    readMethodList = [:[], :binread, :copy_stream, :foreach, :new, :for_fd, :open, :pipe, :popen, :read, :readlines, :sysopen, :try_convert, :each, :each_byte, :each_char, :each_line, :gets, :read, :read_nonblock, :readbyte, :readchar, :readline, :readpartial, :open, :binread, :foreach, :for_fd, :pipe, :read, :readlines, :cp, :copy, :copy_entry, :copy_file, :copy_stream, :cp_r, :open, :gets, :readline, :readlines, :popen2, :popen2e, :popen3]
    methods = tracker.find_call :targets => readTargetList, :methods => readMethodList
    methods.concat tracker.find_call :targets => nil, :method => [:open]
    methods.concat tracker.find_call :targets=>[:IO]
    methods.concat tracker.find_call :targets=>[:"IO.new"]
    


=begin


puts ">>>>> read "
    puts methods
    puts "<<<<"
    puts ">>>> internet"
    puts sendMethods
    puts "<<<<,"

testMethod = tracker.find_call :target => :"Net::HTTP::Post"
  
      puts ">>> methods "
      defins = Sexp.new()
      tracker.controllers.each do |set_name, collection|
        puts set_name
        collection.each_method do |method_name, definition|
          puts method_name #把所有method的名字做成set 然后查里面有没有set的名字
          puts "..........."
          defins = definition[:src] + defins - Sexp.new(:test)
          puts (defins)
          puts ",,,,,,,,"
        end

      end
=end

    
    #m2 = tracker.find_call :targets => :"Net::HTTP", :methods => :get_response
    

    methods.each do |method|
=begin
!!!!!!!!!!!!!!
      puts method[:location][:class]
      puts method[:location][:method]
      puts "........"
=end
      process_result(method)
      end
  end

  def process_result(method)
    return unless original? method
    #puts fileRead
    #puts internetWrite
    message = msg("File read")

      warn :result => method,
        :warning_type => "FileRead",
        :warning_code => :file_access,
        :message => message,
        :confidence => :high,
        :code => method[:call],
        :user_input => ""

  end


end
