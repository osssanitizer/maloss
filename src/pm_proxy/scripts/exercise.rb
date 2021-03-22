# find require string from gem name
# https://stackoverflow.com/questions/5346181/ruby-getting-a-gems-name-for-require
# how executables are specified in rubygems
# https://guides.rubygems.org/specification-reference/#executables
# relationship between gem name and require string
# https://guides.rubygems.org/name-your-gem/
# net-ssh -> required using net/ssh
# gem which $require_string gives library path used by require

require 'timeout'


def get_require_string(pkg_name)
    pkg_name.gsub('-', '/')
end


# Classes and methods
# https://ruby-doc.org/core-2.2.0/Class.html
def try_init_module_attr(mod, attr)
    puts "checking mod #{mod}, attr #{attr}"
    mod.method(attr).call
end


# Ruby timeout
# https://ruby-doc.org/stdlib-2.1.1/libdoc/timeout/rdoc/Timeout.html
def try_init_module_attrs(mod)
    # Find classes available in a Module
    # https://stackoverflow.com/questions/833125/find-classes-available-in-a-module
    # :constants -> list of submodules
    # :const_get(const_name) -> submodule or subclass
    # :class -> (Module, Class, Method)
    # Google::Protobuf.method('methods').class -> Method
    # :public_methods, :public_instance_methods,
    puts "checking mod #{mod}, type #{mod.class}"

    # iterate through submodules
    if mod.class == Module
        # iterate through submodules
        mod.constants.each do |sub_module|
            try_init_module_attrs(mod.const_get(sub_module))
        end

    elsif mod.class == Class
        # iterate through methods
        puts "checking class methods of mod #{mod}"
        inst = nil
        for method in mod.public_methods - mod.public_instance_methods
            begin
                Timeout::timeout(20) do
                    if method == :new
                        inst = try_init_module_attr(mod, method)
                    else
                        try_init_module_attr(mod, method)
                    end
                end
            rescue Timeout::Error
                puts "timeout checking module #{mod}"
            rescue Exception
                puts "error checking module #{mod}"
            end
        end
        if !inst.nil?
            puts "checking instance methods of mod #{mod}"
            for method in mod.public_instance_methods - mod.public_methods
                begin
                    Timeout::timeout(20) do
                        try_init_module_attr(inst, method)
                    end
                rescue Timeout::Error
                    puts "timeout checking module #{mod}"
                rescue Exception
                    puts "error checking module #{mod}"
                end
            end
        end

    elsif mod.class == Method
        puts "checking method mod #{mod}"
        begin
            Timeout::timeout(20) do
                mod.call
            end
        rescue Timeout::Error
            puts "timeout checking module #{mod}"
        rescue Exception
            puts "error checking module #{mod}"
        end

    else
        puts "Unhandled mod #{mod} type #{mod.class}"
    end
end


# Exit handler
# https://stackoverflow.com/questions/1144066/ruby-at-exit-exit-status
# FIXME: add exit handler to process remained modules
def handle_remaining_modules()
    puts "checking remaining modules"
end


at_exit do
    handle_remaining_modules()
end


if __FILE__ == $0
    # OptionParser
    # https://ruby-doc.org/stdlib-2.5.1/libdoc/optparse/rdoc/OptionParser.html
    # http://rubylearning.com/blog/2011/01/03/how-do-i-make-a-command-line-tool-in-ruby/
    if ARGV.length != 1
        puts "Usage: #{$0} PKG_NAME"
        exit
    end

    # import a module by its name
    require_string = get_require_string(ARGV[0])
    old_top_modules = Object.constants
    require require_string
    new_top_modules = Object.constants
    new_modules = new_top_modules - old_top_modules

    # for each module, try to initialize its attributes
    new_modules.each do |new_module|
        try_init_module_attrs(Object.const_get(new_module))
    end
end
