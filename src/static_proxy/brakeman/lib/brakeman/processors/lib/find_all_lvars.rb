require 'brakeman/processors/lib/basic_processor'
require 'ostruct'

class Brakeman::FindALLLVARS < Brakeman::BasicProcessor
  attr_reader :calls

  def initialize tracker
    super
    @current_class = nil
    @current_method = nil
    @in_target = false
    @cache = {}
    @args = {}
  end

  def get_all_lvars
    @args.each do |k, vs|
      @args[k] = vs.sort_by{|v| -v.line}
    end
    @args
  end

  #Process the given source. Provide either class and method being searched
  #or the template. These names are used when reporting results.
  def process_source exp, opts
    @current_class = opts[:class]
    @current_method = opts[:method]
    @current_template = opts[:template]
    @current_file = opts[:file]
    @current_call = nil
    process exp
  end

  #Process body of method

  def make_location
    if @current_template
      key = [@current_template, @current_file]
      cached = @cache[key]
      return cached if cached

      @cache[key] = { :type => :template,
        :template => @current_template,
        :file => @current_file }
    else
      key = [@current_class, @current_method, @current_file]
      cached = @cache[key]
      return cached if cached
      @cache[key] = { :type => :class,
        :class => @current_class,
        :method => @current_method,
        :file => @current_file }
    end

  end
  

  def make_location_struct line
    location = make_location
    struct = OpenStruct.new
    struct.class_name = location[:class]
    struct.method_name = location[:method]
    struct.file = location[:file]
    struct.line = line
    struct
  end


  def process_lvar exp
    location = make_location_struct exp.line
    @args[exp[1]] ||= []
    @args[exp[1]] << location
    exp
  end


end
