require 'brakeman/checks/base_check'
require 'brakeman/processors/lib/processor_helper'

#Checks for user input in methods which open or manipulate files
class Brakeman::CheckInternetRead < Brakeman::BaseCheck
  Brakeman::Checks.add self


  def run_check
    Brakeman.debug "Finding possible file access"
    targetList = [:Socket,:TCPSocket,:UDPSocket,:udp_server_recv,:TCPServer,:"Net::FTP",:"Net::HTTP",:"Net::HTTPGenericRequest",:"Net::HTTPRequest",:"Net::HTTP::Get",:"Net::HTTP::Post",:"Net::IMAP",:"Net::POP3",]
    methodList = [:[], :recv, :recv_nonblock, :recvmsg, :recvmsg_nonblock, :recvfrom, :tcp, :tcp_server_loop, :tcp_server_sockets, :udp_server_loop, :udp_server_loop_on, :udp_server_recv, :udp_server_sockets, :accept, :accept_nonblock, :getbinaryfile, :getdir, :gettextfile, :retrbinary, :retrlines, :sendcmd, :get, :get2, :get_print, :get_response, :post, :post_form, :post2, :request, :request_get, :request_head, :request_post, :fetch, :uid_fetch, :start, :pop]
    methods = tracker.find_call :targets => targetList, :methods => methodList
    methods.concat tracker.find_call :targets => nil, :method => [:open]
    methods.concat tracker.find_call :targets=>[:Socket,:UDPSocket,:TCPSocket,:TCPServer,:"Net::HTTPGenericRequest",:"Net::HTTPRequest",:"Net::HTTP::Get",:"Net::HTTP::Post",:"Net::POP3",]
    methods.concat tracker.find_call :targets=>[:"Socket.new",:"UDPSocket.new",:"TCPSocket.new",:"TCPServer.new",:"Net::HTTPGenericRequest.new",:"Net::HTTPRequest.new",:"Net::HTTP::Get.new",:"Net::HTTP::Post.new",:"Net::POP3.new",]
    


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
    message = msg("Internet Read")

      warn :result => method,
        :warning_type => "InternetRead",
        :warning_code => :file_access,
        :message => message,
        :confidence => :high,
        :code => method[:call],
        :user_input => ""

  end


end
