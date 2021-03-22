
# https://rubymonk.com/learning/books/5-metaprogramming-ruby-ascent/chapters/24-eval/lessons/63-eval

def read_file(file_name)
  file = File.open(file_name, "r")
  data = file.read
  file.close
  return data
end

puts "Start"
puts read_file("/tmp/log/test.log")
puts "End"

s = system 'uptime'









contents = Document.new('zen').get_contents
puts contents
puts eval(contents)



def get_binding
 binding
end

class Monk
  def get_binding
    binding
  end
end

puts eval("self", get_binding)
puts eval("self", Monk.new.get_binding)



# TOPLEVEL_BINDING
class RubyMonk
  def self.create_book(book)
    eval("def #{book}; 'created'; end", TOPLEVEL_BINDING)
  end
end

RubyMonk.create_book :regular_expressions

puts regular_expressions

result = RubyMonk.new
data = result.create_book :hello_world
puts data


# https://medium.com/the-renaissance-developer/ruby-101-data-structures-7705d82ec1
bookshelf = []
bookshelf.push("The Effective Engineer")
bookshelf.push("The 4 hours work week")
print bookshelf[0] # The Effective Engineer
print bookshelf[1] # The 4 hours work week
bookshelf << "Hooked"
bookshelf.<<("Hooked")
print bookshelf[2]
print bookshelf[3]

bookshelf = [
  "The Effective Engineer",
  "The 4 hours work week",
  "Zero to One",
  "Lean Startup",
  "Hooked"
]

bookshelf.each do |book|
  puts book
end

hash_tk = {
  "name" => "Leandro",
  "nickname" => "Tk",
  "nationality" => "Brazilian",
  "age" => 24
}

hash_tk.each do |attribute, value|
  puts "#{attribute}: #{value}"
end


# function
def hello_world(x, y)
    puts "x+y is: ", x+y
    return x+y
end

good = hello_world(3, 5)
puts good


# define it
def variable_args(arg1, *more)
  puts more
end

# call it
variable_args(1,2,3,4)


# Open3.popen3
require 'open3'
cmd = 'git push heroku master'
Open3.popen3(cmd) do |stdin, stdout, stderr, wait_thr|
      puts "stdout is:" + stdout.read
        puts "stderr is:" + stderr.read
end

