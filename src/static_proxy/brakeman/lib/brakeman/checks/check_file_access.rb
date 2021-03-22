require 'brakeman/checks/base_check'
require 'brakeman/processors/lib/processor_helper'

#Checks for user input in methods which open or manipulate files
class Brakeman::CheckFileAccess < Brakeman::BaseCheck
  Brakeman::Checks.add self

  @description = "Finds possible file access using user input"

  def run_check
    Brakeman.debug "Finding possible file access"
    methods = tracker.find_call :targets => [:Dir, :File, :IO, :Kernel, :"Net::FTP", :"Net::HTTP", :PStore, :Pathname, :Shell], :methods => [:[], :chdir, :chroot, :delete, :entries, :foreach, :glob, :install, :lchmod, :lchown, :link, :load, :load_file, :makedirs, :move, :new, :open, :read, :readlines, :rename, :rmdir, :safe_unlink, :symlink, :syscopy, :sysopen, :truncate, :unlink]
=begin
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


    #puts methods.class

    m2 = tracker.find_call :targets => :"Net::HTTP", :methods => :get_response
    #puts ">>>>>>>>> m2"
    #puts m2 # 可以check 他们跟上面的string有没有match
    #puts "<<<<<<<"

    methods.concat tracker.find_call :target => :YAML, :methods => [:load_file, :parse_file]
    methods.concat tracker.find_call :target => nil, :method => [:open]

    Brakeman.debug "Finding calls to load()"
    methods.concat tracker.find_call :target => false, :method => :load

    Brakeman.debug "Finding calls using FileUtils"
    methods.concat tracker.find_call :target => :FileUtils

    Brakeman.debug "Processing found calls"
    methods.each do |call|
      process_result call
    end
  end

  def process_result result
    return unless original? result
    call = result[:call]

    file_name = call.first_arg

    #puts ">>>>>>>>>> block"
    #puts result[:block]#跟 call 一样返回的都是一个一个的string 在checks/base_check.rb 里做match check

    #puts ">>> file_name "
    #puts file_name
    #puts "<<<<"

    return if called_on_tempfile?(file_name)

    if match = has_immediate_user_input?(file_name)
      confidence = :high
    elsif match = has_immediate_model?(file_name)
      match = Match.new(:model, match)
      confidence = :medium
    elsif tracker.options[:check_arguments] and
      match = include_user_input?(file_name)

      #Check for string building in file name
      if call?(file_name) and (file_name.method == :+ or file_name.method == :<<)
        #puts ">>> here "
      #puts file_name
      #puts "<<<<"
        confidence = :high
      else
        confidence = :weak
      end
    end

    if match and not temp_file_method? match.match

      message = msg(msg_input(match), " used in file name")

      warn :result => result,
        :warning_type => "File Access",
        :warning_code => :file_access,
        :message => message,
        :confidence => confidence,
        :code => call,
        :user_input => match
    end
  end

  # When using Tempfile, there is no risk of unauthorized file access, since
  # Tempfile adds a unique string onto the end of every provided filename, and
  # ensures that the filename does not already exist in the system.
  def called_on_tempfile? file_name
    call?(file_name) && file_name.target == s(:const, :Tempfile)
  end

  def temp_file_method? exp
    if call? exp
      return true if exp.call_chain.include? :tempfile

      params? exp.target and exp.method == :path
    end
  end
end
