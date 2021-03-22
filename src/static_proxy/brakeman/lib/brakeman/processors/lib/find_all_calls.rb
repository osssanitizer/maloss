require 'brakeman/processors/lib/basic_processor'
require 'ostruct'

class Brakeman::FindAllCalls < Brakeman::BasicProcessor
  attr_reader :calls

  def initialize tracker
    super

    @in_target = false
    @processing_class = false
    @calls = []
    @cache = {}
    @assignment = {}
    @line_code = {}
  end 

  def get_line_code
    @line_code
  end
=begin
  def process_assignment_vals
    puts ">>>>"
    puts @args
    puts @line_code
    puts @assignment

    @assignment.each do |key,values|
      struct = OpenStruct.new
      struct.val = key
      values = values.sort_by {|v| -v.line}
      values.each do |value|
        location = value.class_name.to_s+","+value.method_name.to_s+","+value.file.to_s+","+value.line.to_s
        struct.definiation = @line_code[location]
        used_locations = @args[key]
        used_locations = used_locations.sort_by{|l| -l.line}
        struct.used_locations = []
        used_locations.each do |location|
          next if location.class_name != value.class_name || location.method_name != value.method_name || location.file != value.file || location.line < value.line
          location = location.class_name.to_s+","+location.method_name.to_s+","+location.file.to_s+","+location.line.to_s
          struct.used_locations << @line_code[location]
        end
      end
      puts struct
    end

    @assignment
  end
=end
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

  #For whatever reason, originally the indexing of calls
  #was performed on individual method bodies (see process_defn).
  #This method explicitly indexes all calls everywhere given any
  #source.
  def process_all_source exp, opts
    @processing_class = true
    process_source exp, opts
  ensure
    @processing_class = false
  end

  #Process body of method
  def process_defn exp
    return exp unless @current_method or @processing_class

    # 'Normal' processing assumes the method name was given
    # as an option to `process_source` but for `process_all_source`
    # we don't want to do that.
    if @current_method.nil?
      @current_method = exp.method_name
      process_all exp.body
      @current_method = nil
    else
      process_all exp.body
    end

    exp
  end

  alias process_defs process_defn

  #Process body of block
  def process_rlist exp
    process_all exp
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



  def process_call exp
    location = make_location[:class].to_s + ","+make_location[:method].to_s + "," + make_location[:file].to_s+","
    if @line_code[location + exp.line.to_s].nil?
      @line_code[location + exp.line.to_s] = exp 
    else
      old_exp = @line_code[location + exp.line.to_s]
      if Brakeman::OutputProcessor.new.format(exp).include?(Brakeman::OutputProcessor.new.format(old_exp))
        @line_code[location + exp.line.to_s] = exp 
      end
    end

    @calls << create_call_hash(exp)
    exp
  end

  def process_iter exp
    call = exp.block_call

    if call.node_type == :call
      call_hash = create_call_hash(call)

      call_hash[:block] = exp.block
      call_hash[:block_args] = exp.block_args

      @calls << call_hash

      process exp.block
    else
      #Probably a :render call with block
      process call
      process exp.block
    end

    exp
  end

  #Calls to render() are converted to s(:render, ...) but we would
  #like them in the call cache still for speed
  def process_render exp
    process exp.last if sexp? exp.last

    add_simple_call :render, exp

    exp
  end

  #Technically, `` is call to Kernel#`
  #But we just need them in the call cache for speed
  def process_dxstr exp
    process exp.last if sexp? exp.last

    add_simple_call :`, exp

    exp
  end

  def process_xstr exp
    process exp.last if sexp? exp.last

    add_simple_call :builtin_xstring, exp

    exp
  end

  #:"string" is equivalent to "string".to_sym
  def process_dsym exp
    exp.each { |arg| process arg if sexp? arg }

    add_simple_call :literal_to_sym, exp

    exp
  end

  # Process a dynamic regex like a call
  def process_dregx exp
    exp.each { |arg| process arg if sexp? arg }

    add_simple_call :brakeman_regex_interp, exp

    exp
  end

  #Process an assignment like a call
  def process_attrasgn exp
    process_call exp
  end

  private

  def add_simple_call method_name, exp
    @calls << { :target => nil,
                :method => method_name,
                :call => exp,
                :nested => false,
                :location => make_location,
                :parent => @current_call }
  end

  #Gets the target of a call as a Symbol
  #if possible
  def get_target exp, include_calls = false
    if sexp? exp
      case exp.node_type
      when :ivar, :lvar, :const, :lit
        exp.value
      when :true, :false
        exp[0]
      when :colon2
        class_name exp
      when :self
        @current_class || @current_module || nil
      when :params, :session, :cookies
        exp.node_type
      when :call, :safe_call
        if include_calls
          if exp.target.nil?
            exp.method
          else
            t = get_target(exp.target, :include_calls)
            if t.is_a? Symbol
              :"#{t}.#{exp.method}"
            else
              exp
            end
          end
        else
          exp
        end
      else
        exp
      end
    else
      exp
    end
  end

  #Returns method chain as an array
  #For example, User.human.alive.all would return [:User, :human, :alive, :all]
  def get_chain call
    if node_type? call, :call, :attrasgn, :safe_call, :safe_attrasgn
      get_chain(call.target) + [call.method]
    elsif call.nil?
      []
    else
      [get_target(call)]
    end
  end

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

  #Return info hash for a call Sexp
  def create_call_hash exp, assignment=nil
    target = get_target exp.target


    if call? target or node_type? target, :dxstr # need to index `` even if target of a call
      already_in_target = @in_target
      @in_target = true
      process target
      @in_target = already_in_target

      target = get_target(target, :include_calls)
    end

    method = exp.method

    call_hash = {
      :target => target,
      :method => method,
      :call => exp,
      :nested => @in_target,
      :chain => get_chain(exp),
      :location => make_location,
      :parent => @current_call,
      :assignment => assignment
    }

    old_parent = @current_call
    @current_call = call_hash

    process_call_args exp

    @current_call = old_parent

    call_hash
  end
end
