require 'set'
require 'brakeman/call_index'
require 'brakeman/checks'
require 'brakeman/report'
require 'brakeman/processors/lib/find_call'
require 'brakeman/processors/lib/find_all_calls'
require 'brakeman/processors/lib/find_all_lvars'
require 'brakeman/processors/lib/find_all_lasgn'
require 'brakeman/tracker/config'
require 'brakeman/tracker/constants'

#The Tracker keeps track of all the processed information.
class Brakeman::Tracker
  attr_accessor :controllers, :constants, :templates, :models, :errors,
    :checks, :initializers, :config, :routes, :processor, :libs,
    :template_cache, :options, :filter_cache, :start_time, :end_time,
    :duration, :ignored_filter, :app_tree

  #Place holder when there should be a model, but it is not
  #clear what model it will be.
  UNKNOWN_MODEL = :BrakemanUnresolvedModel

  #Creates a new Tracker.
  #
  #The Processor argument is only used by other Processors
  #that might need to access it.
  def initialize(app_tree, processor = nil, options = {})
    @app_tree = app_tree
    @processor = processor
    @options = options

    @config = Brakeman::Config.new(self)
    @templates = {}
    @controllers = {}
    #Initialize models with the unknown model so
    #we can match models later without knowing precisely what
    #class they are.
    @models = {}
    @models[UNKNOWN_MODEL] = Brakeman::Model.new(UNKNOWN_MODEL, nil, @app_tree.file_path("NOT_REAL.rb"), nil, self)
    @routes = {}
    @initializers = {}
    @errors = []
    @libs = {}
    @constants = Brakeman::Constants.new
    @checks = nil
    @processed = nil
    @template_cache = Set.new
    @filter_cache = {}
    @call_index = nil
    @start_time = Time.now
    @end_time = nil
    @duration = nil
    @visited = Set.new()
    @assignment_vals = {}
  end

  #Add an error to the list. If no backtrace is given,
  #the one from the exception will be used.
  def error exception, backtrace = nil
    backtrace ||= exception.backtrace
    unless backtrace.is_a? Array
      backtrace = [ backtrace ]
    end

    Brakeman.debug exception
    Brakeman.debug backtrace

    @errors << {
      :exception => exception,
      :error => exception.to_s.gsub("\n", " "),
      :backtrace => backtrace
    }
  end

  #Run a set of checks on the current information. Results will be stored
  #in Tracker#checks.
  def run_checks
    @checks = Brakeman::Checks.run_checks(self)
    @end_time = Time.now
    @duration = @end_time - @start_time
    @checks
  end

  def app_path
    @app_path ||= File.expand_path @options[:app_path]
  end

  #Iterate over all methods in controllers and models.
  def each_method
    classes = [self.controllers, self.models]

    if @options[:index_libs]
      classes << self.libs
    end

    classes.each do |set|
      set.each do |set_name, collection|
        collection.each_method do |method_name, definition|
          src = definition[:src]
          yield src, set_name, method_name, definition[:file]
        end
      end
    end
  end

  #Iterates over each template, yielding the name and the template.
  #Prioritizes templates which have been rendered.
  def each_template
    if @processed.nil?
      @processed, @rest = templates.keys.sort_by{|template| template.to_s}.partition { |k| k.to_s.include? "." }
    end

    @processed.each do |k|
      yield k, templates[k]
    end

    @rest.each do |k|
      yield k, templates[k]
    end
  end


  def each_class
    classes = [self.controllers, self.models]

    if @options[:index_libs]
      classes << self.libs
    end

    classes.each do |set|
      set.each do |set_name, collection|
        collection.src.each do |file, src|
          yield src, set_name, file
        end
      end
    end
  end

  #Find a method call.
  #
  #Options:
  #  * :target => target name(s)
  #  * :method => method name(s)
  #  * :chained => search in method chains
  #
  #If :target => false or :target => nil, searches for methods without a target.
  #Targets and methods can be specified as a symbol, an array of symbols,
  #or a regular expression.
  #
  #If :chained => true, matches target at head of method chain and method at end.
  #
  #For example:
  #
  #    find_call :target => User, :method => :all, :chained => true
  #
  #could match
  #
  #    User.human.active.all(...)
  #
  def find_call options
    index_call_sites unless @call_index
    @call_index.find_calls options
  end

  #Searches the initializers for a method call
  def check_initializers target, method
    finder = Brakeman::FindCall.new target, method, self

    initializers.sort.each do |name, initializer|
      finder.process_source initializer
    end

    finder.matches
  end

  #Returns a Report with this Tracker's information
  def report
    Brakeman::Report.new(self)
  end

  def warnings
    self.checks.all_warnings
  end

  def filtered_warnings
    if self.ignored_filter
      self.warnings.reject do |w|
        self.ignored_filter.ignored? w
      end
    else
      self.warnings
    end
  end

  def unused_fingerprints
    return [] unless self.ignored_filter
    self.ignored_filter.obsolete_fingerprints
  end

  def add_constant name, value, context = nil
    @constants.add name, value, context unless @options[:disable_constant_tracking]
  end

  def constant_lookup name
    @constants.get_literal name unless @options[:disable_constant_tracking]
  end

  def find_class name
    [@controllers, @models, @libs].each do |collection|
      if c = collection[name]
        return c
      end
    end

    nil
  end

  def index_call_sites
    finder = Brakeman::FindAllCalls.new self


    self.each_method do |definition, set_name, method_name, file|
      finder.process_source definition, :class => set_name, :method => method_name, :file => file
    end

    self.each_class do |definition, set_name, file|
      finder.process_source definition, :class => set_name, :file => file
    end

    self.each_template do |_name, template|
      finder.process_source template.src, :template => template, :file => template.file
    end

    self.initializers.each do |file_name, src|
      finder.process_all_source src, :file => file_name
    end

    @call_index = Brakeman::CallIndex.new finder.calls
    #@assignment_vals = finder.process_assignment_vals
    @codes = finder.get_line_code
    process_vals @codes
     
  end


  def process_vals codes
    @vals = {}
    defs = get_all_lasgn
    vars = get_all_lvars

    defs.each do |key,values|
      next if vars[key].nil?
      @vals[key] ||= []
      values.each do |value|

        struct = OpenStruct.new
        struct.val = key
        location = value.class_name.to_s+","+value.method_name.to_s+","+value.file.to_s+","+value.line.to_s
        struct.definiation = codes[location]
        used_locations = vars[key]
        struct.used_locations = []
        to_be_delete_locations = []
        used_locations.each do |location|
          next if location.class_name != value.class_name || location.method_name != value.method_name || location.file != value.file || location.line < value.line

          location_info = location.class_name.to_s+","+location.method_name.to_s+","+location.file.to_s+","+location.line.to_s
          struct.used_locations << codes[location_info]
          to_be_delete_locations << location
        end

        to_be_delete_locations.each do |location|
          vars[key].delete(location)
        end

        @vals[key] << struct
      end
    end
    @vars = vars
    @vals
  end

  def find_block_args arg_name, exp
    block_code = Brakeman::OutputProcessor.new.format(exp)
    block_args_code = []
    used_locations = @vars[arg_name]
    return nil if used_locations.nil?
    used_locations.each do |location|
      location_info = location.class_name.to_s+","+location.method_name.to_s+","+location.file.to_s+","+location.line.to_s
      code = @codes[location_info]
      next if !block_code.include?(Brakeman::OutputProcessor.new.format(code))
      block_args_code << code
    end
    block_args_code
  end

  def find_val exp
    
    target = Brakeman::OutputProcessor.new.format(exp)
    @vals.each do |k, vs|
      vs.each do |v|
        return v if v.definiation == exp
      end
    end
    return nil
  end


  def get_all_lvars
    lvars = Brakeman::FindALLLVARS.new self
    self.each_method do |definition, set_name, method_name, file|
      lvars.process_source definition, :class => set_name, :method => method_name, :file => file
    end

    self.each_class do |definition, set_name, file|
      lvars.process_source definition, :class => set_name, :file => file
    end

    self.each_template do |_name, template|
      lvars.process_source template.src, :template => template, :file => template.file
    end
    lvars.get_all_lvars
  end


  def get_all_lasgn
    lvars = Brakeman::FindALLLASGN.new self
    self.each_method do |definition, set_name, method_name, file|
      lvars.process_source definition, :class => set_name, :method => method_name, :file => file
    end

    self.each_class do |definition, set_name, file|
      lvars.process_source definition, :class => set_name, :file => file
    end

    self.each_template do |_name, template|
      lvars.process_source template.src, :template => template, :file => template.file
    end
    lvars.get_all_lasgns
  end


  #Reindex call sites
  #
  #Takes a set of symbols which can include :templates, :models,
  #or :controllers
  #
  #This will limit reindexing to the given sets
  def reindex_call_sites locations
    #If reindexing templates, models, controllers,
    #just redo everything.
    if locations.length == 3
      return index_call_sites
    end

    if locations.include? :templates
      @call_index.remove_template_indexes
    end

    classes_to_reindex = Set.new
    method_sets = []

    if locations.include? :models
      classes_to_reindex.merge self.models.keys
      method_sets << self.models
    end

    if locations.include? :controllers
      classes_to_reindex.merge self.controllers.keys
      method_sets << self.controllers
    end

    if locations.include? :initializers
      self.initializers.each do |file_name, src|
        @call_index.remove_indexes_by_file file_name
      end
    end

    @call_index.remove_indexes_by_class classes_to_reindex

    finder = Brakeman::FindAllCalls.new self

    method_sets.each do |set|
      set.each do |set_name, info|
        info.each_method do |method_name, definition|
          src = definition[:src]
          finder.process_source src, :class => set_name, :method => method_name, :file => definition[:file]
        end
      end
    end

    if locations.include? :templates
      self.each_template do |_name, template|
        finder.process_source template.src, :template => template, :file => template.file
      end
    end

    if locations.include? :initializers
      self.initializers.each do |file_name, src|
        finder.process_all_source src, :file => file_name
      end
    end

    @call_index.index_calls finder.calls
  end

  #Clear information related to templates.
  #If :only_rendered => true, will delete templates rendered from
  #controllers (but not those rendered from other templates)
  def reset_templates options = { :only_rendered => false }
    if options[:only_rendered]
      @templates.delete_if do |_name, template|
        template.rendered_from_controller?
      end
    else
      @templates = {}
    end
    @processed = nil
    @rest = nil
    @template_cache.clear
  end

  #Clear information related to template
  def reset_template name
    name = name.to_sym
    @templates.delete name
    @processed = nil
    @rest = nil
    @template_cache.clear
  end

  #Clear information related to model
  def reset_model path
    model_name = nil

    @models.each do |name, model|
      if model.files.include?(path)
        model_name = name
        break
      end
    end

    @models.delete model_name
  end

  #Clear information related to model
  def reset_lib path
    lib_name = nil

    @libs.each do |name, lib|
      if lib.files.include?(path)
        lib_name = name
        break
      end
    end

    @libs.delete lib_name
  end

  def reset_controller path
    controller_name = nil

    #Remove from controller
    @controllers.each do |name, controller|
      if controller.files.include?(path)
        controller_name = name

        #Remove templates rendered from this controller
        @templates.each do |template_name, template|
          if template.render_path and template.render_path.include_controller? name
            reset_template template_name
            @call_index.remove_template_indexes template_name
          end
        end

        #Remove calls indexed from this controller
        @call_index.remove_indexes_by_class [name]
        break
      end
    end
    @controllers.delete controller_name
  end

  #Clear information about routes
  def reset_routes
    @routes = {}
  end

  # fun a( b()) a: parent b: children
  def isChildren(childrenMethod, parentMethod, pnodes)

    #puts "Pnodes"
    #puts pnodes
    #puts childrenMethod

    pnodes << childrenMethod
    pnodes << parentMethod

    #puts "Pnodes2"
    #puts pnodes
    #puts childrenMethod

    return isDifferentFunctionMatch(childrenMethod,parentMethod, pnodes) if parentMethod[:location][:method] != childrenMethod[:location][:method]
    parent = Brakeman::OutputProcessor.new.format(parentMethod[:call])
    children = Brakeman::OutputProcessor.new.format(childrenMethod[:call]) 


      #args = parentMethod[:call].args.each do |arg|
        #puts Brakeman::OutputProcessor.new.format(arg) 
        #puts "ooooo~~~" if arg.include? (childrenMethod[:call])
      #end
=begin
      if childrenMethod[:call].line == 9 && parentMethod[:call].line == 10
      puts "src....."
      puts childrenMethod
      puts "sink....."
      puts parentMethod
      if !childrenMethod[:parent].nil?
        puts "oooooo```" if Brakeman::OutputProcessor.new.format(parentMethod[:parent][:call]).include?(children)
      end
    end

=end 


    #return true if(parent.include? children)
    if !childrenMethod[:parent].nil?
      return true if Brakeman::OutputProcessor.new.format(childrenMethod[:parent][:call]).include?(parent) && parent != children
    end
    begin
    parentMethod[:call].args.each do |arg|
        sink_args = Brakeman::OutputProcessor.new.format(arg) 
        return true if sink_args.include?(children)
    end
  rescue
  end

    
    return true if check_args_with_source(childrenMethod, parentMethod, pnodes)

    return true if check_block(childrenMethod, parentMethod, pnodes)
    
=begin    
    while childrenMethod do
      call = childrenMethod[:call]
      children = Brakeman::OutputProcessor.new.format(call)
      return true if (children.include? parent)

      childrenMethod = childrenMethod[:parent]
    end
=end

      return false
  end

  def code_eq?(src_code, sink_code)
    return true if Brakeman::OutputProcessor.new.format(src_code) == Brakeman::OutputProcessor.new.format(sink_code)
  end

  def check_block(source, sink, pnodes)
    src_args = source[:block_args]
    sink_args = sink[:block_args]
    return false if src_args.nil? && sink_args.nil?

    if !src_args.nil? && sink_args.nil?
      (1..src_args.length-1).each do |n|
        used_lists = find_block_args src_args[n], source[:block]
        next if used_lists.nil?
        used_lists.each do |l|
          new_source = {}
          new_source[:call] = l
          new_source[:location] = source[:location]
          return true if isChildren(new_source, sink, pnodes)
        end
      end
    elsif !sink_args.nil? && src_args.nil?
      (1..sink_args.length-1).each do |n|
        used_lists = find_block_args sink_args[n], sink[:block]
        next if used_lists.nil?
        used_lists.each do |l|
          new_sink = {}
          new_sink[:call] = l
          new_sink[:location] = sink[:location]
          #return true if l == source[:call]
          #return true if code_eq?(source[:call], new_sink[:call])
          return true if isChildren(source, new_sink, pnodes)
        end
      end

    else
      (1..src_args.length-1).each do |src_n|
        src_used_lists = @vars[src_args[src_n]]
        next if src_used_lists.nil?
        (1..sink_args.length-1).each do |sink_n|
          sink_used_lists = @vars[sink_args[sink_n]]
          next if sink_used_lists.nil?
          src_used_lists.each do |src_l|
            sink_used_lists.each do |sink_l|
              new_source = {}
              new_source[:call] = src_l
              new_source[:location] = source[:location]
              new_sink = {}
              new_sink[:call] = sink_l
              new_sink[:location] = sink[:location]
              #return true if src_l == sink_l
              #return true if code_eq?(new_source[:call], new_sink[:call])
              return true if isChildren(new_source, new_sink, pnodes)
            end
          end
        end
      end
    end
    return false
  end


  def check_args_with_source(source, sink, pnodes)

    source_struct = find_val source[:call]
    sink_struct = find_val sink[:call]
    
    return false if source_struct.nil? && sink_struct.nil?

    if !source_struct.nil? && sink_struct.nil?
      #puts "source, !sink"
      source_struct.used_locations.each do |location|
        new_source = {}
        new_source[:call] = location
        new_source[:location] = source[:location]
        #return true if code_eq?(new_source[:call], sink[:call])
        return true if isChildren(new_source, sink, pnodes)
      end
    elsif !sink_struct.nil? && source_struct.nil?
      sink_struct.used_locations.each do |sink_location|
        new_sink = {}
        new_sink[:call] = sink_location
        new_sink[:location] = sink[:location]
        #return true if code_eq?(source[:call], new_sink[:call])
        return true if isChildren(source, new_sink, pnodes)
      end
    else
      #puts "source, sink"
      source_struct.used_locations.each do |location|
      sink_struct.used_locations.each do |sink_location|
        new_source = {}
        new_source[:call] = location
        new_source[:location] = source[:location]
        new_sink = {}
        new_sink[:call] = sink_location
        new_sink[:location] = sink[:location]
      #puts "try/////  "
      #puts Brakeman::OutputProcessor.new.format(new_source[:call])
        #puts "true!!!" if isChildren(new_source, new_sink)
        #return true if code_eq?(new_source[:call], new_sink[:call])
        return true if isChildren(new_source, new_sink, pnodes)
      end
    end
    end
    return false
    #args.each do |arg|
    #    puts arg
    #end
  end

  def isDifferentFunctionMatch(source, sink, pnodes)


    return false if source[:location][:class] == :nil || sink[:location][:class] == :nil

    source_sink_info = "src_target: " + source[:location][:class].to_s + " src_method: " + source[:location][:method].to_s + 
      " sink_target: " + sink[:location][:class].to_s + " sink_method: " + sink[:location][:method].to_s 
      
    return false if @visited.include?(source_sink_info)

    @visited << source_sink_info

      #puts "...src...."
        #puts source
        #puts "sink_m,,,,,,,"
        #puts sink

    source_removeDot = /(?<=\.)[\w+.-]+/.match(source[:location][:method])
    src_methods = [source]
    if source[:location][:method].nil?
      src_methods.concat(find_call :targets => [nil, :self, source[:location][:class]])
    else
      src_methods.concat(find_call :targets => [nil, :self, source[:location][:class]],:methods => source[:location][:method])
    end
    if source_removeDot
      src_methods.concat(find_call :targets => [nil, :self, source[:location][:class]],:methods => source_removeDot[0].to_sym)
    end


    sink_removeDot = /(?<=\.)[\w+.-]+/.match(sink[:location][:method])
    sink_methods = [sink]
    if sink[:location][:method].nil?
      sink_methods.concat(find_call :targets => [nil, :self, sink[:location][:class]])
    else
      sink_methods.concat(find_call :targets => [nil, :self, sink[:location][:class]], :methods => sink[:location][:method])
    end
    if sink_removeDot
      sink_methods.concat(find_call :targets => [nil, :self, sink[:location][:class]], :methods => sink_removeDot[0].to_sym)
    end


    src_methods.each do |src_m|
      sink_methods.each do |sink_m|
        #puts "...src...."
        #puts src_m
        #puts "sink_m,,,,,,,"
        #puts sink_m
        return true if isChildren(src_m, sink_m, pnodes)
      end
    end
    return false

      


  end


=begin
  def isDifferentFunctionMatch(children, parent)
    #if @methodResult[children] != nil
    #  return @methodResult[children]
    #end
    
    if includeInput?(parent[:call])
      removeDot = /(?<=\.)[\w+.-]+/.match(parent[:location][:method])
      methodList = [parent[:location][:method]]
      if removeDot
        methodList << removeDot[0]
      end

      methods = find_call :targets => [nil, :self, parent[:location][:class]], :methods => methodList
      


      for method in methods
        return true if isDifferentFunctionMatch(children, method)
      end
    end

    controlerProcessor = Brakeman::ControllerAliasProcessor.new(@app_tree, self)
//=begin
    puts ">>>>>> parent"
    puts Brakeman::OutputProcessor.new.format(parent[:call])
    puts parent
//=end
    targetClass = parent[:location][:class]
    targetMethod = parent[:location][:method]
    if /(?<=\.)[\w+.-]+/.match(targetMethod)
      targetMethod = /(?<=\.)[\w+.-]+/.match(targetMethod)[0]
    end
    childrenClass = children[:location][:class]
    childrenMethod = children[:location][:method]
    if /(?<=\.)[\w+.-]+/.match(childrenMethod)
      childrenMethod = /(?<=\.)[\w+.-]+/.match(childrenMethod)[0]
    end
    childrenStr = Brakeman::OutputProcessor.new.format(children[:call])
//=begin
    puts ">>>>>> children"
    puts childrenStr
    puts children
    puts "<<<<<<<<<"
//=end
    #return false if @visited.include?(childrenStr)
    @visited.add(childrenStr)
    #puts @visited.inspect

    if childrenMethod == targetMethod && childrenClass == targetClass
      return true if isChildren(children, parent)
    end

    targets = [nil, :self, childrenClass.to_sym]
    m = childrenMethod.to_sym if !childrenMethod.nil?
    methods = find_call :targets => targets, :methods => m
//=begin
    puts ">>> methods >>>>"
    puts "childrenClass "
    puts childrenClass
    puts " targetClass "
    puts targetClass
    puts " childrenMethod "
    puts childrenMethod
    ms = find_call  :methods => :post3
    puts " ms   !!!!"
    puts ms
    puts methods
    puts "<< methods <<<<<"
//=end    
    for method in methods

      if method[:location][:method] != targetMethod || method[:location][:class] != targetClass

        if isDifferentFunctionMatch(method, parent)
          #@methodResult[method] = true
          return true 
        end
      end
      #puts method[:location][:method]
      #puts targetMethod
      #puts method
      #puts ".........."
      if isChildren(method, parent)
        #@methodResult[method] = true
        return true 
      end
    end
    #@methodResult[children] = false
    return false
  end
=end

  def includeInput? exp
    match = Struct.new(:type, :match)
    if exp.nil?
      false
    elsif processor.call? exp
      return true if match.new(:lvar, exp) != nil
      includeInput? exp.target
    elsif processor.sexp? exp
      return true if match.new(:lvar, exp) != nil
    else
      return false
    end
  end

  def reset_initializer path
    @initializers.delete_if do |file, src|
      path.relative.include? file
    end

    @call_index.remove_indexes_by_file path
  end
end

