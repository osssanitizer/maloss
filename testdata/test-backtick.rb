# Ruby, Difference between exec, system and %x() or Backticks
# https://stackoverflow.com/questions/6338908/ruby-difference-between-exec-system-and-x-or-backticks

# output to stdout
system("ls -alxh")

# output to variable
res = `ls -alxh`
p 'backtick: ' + res

res = %x(ls -alxh)
p '%x(): ' + res

res = %x{ls -alxh}
p '%x{}: ' + res

%x-date-
p '%s--: ' + res

require 'open3'

Open3.popen3("curl http://example.com") do |stdin, stdout, stderr, thread|
   pid = thread.pid
   p 'Open3.popen3: ' + stdout.read.chomp
end

# no code can be run after exec
exec("date")
