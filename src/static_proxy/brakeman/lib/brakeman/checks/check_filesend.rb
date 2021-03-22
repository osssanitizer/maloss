require 'brakeman/checks/base_check'
require 'brakeman/processors/lib/processor_helper'

#Checks for user input in methods which open or manipulate files
class Brakeman::CheckFileSend < Brakeman::BaseCheck
  Brakeman::Checks.add self

  @description = "Finds possible file read and send to internet"

  def run_check
    sendTargetList = [:Socket,:TCPServer,:TCPSocket,:UDPSocket,:"Net::HTTP::Put",:"Net::FTP",:"Net::HTTP",:"Net::HTTPGenericRequest",:"Net::HTTPRequest",:"Net::IMAP",:"Net::SMTP"]
    sendMethodList = [:[], :sysaccept,:tcp,:tcp_server_loop,:tcp_server_sockets,:udp_server_loop,:udp_server_loop_on,:udp_server_recv,:udp_server_sockets,:accept,:accept_nonblock,:send,:sendmsg,:sendmsg_nonblock,:put,:putbinaryfile,:puttextfile,:storbinary,:storlines,:post,:post_form,:post2,:request_post,:request_get,:request_head,:send_request,:request, :append,:data,:send_mail,:send_message,:sendmail,:open_message_stream,:ready,]
    sendMethods = tracker.find_call :targets => sendTargetList, :methods => sendMethodList
    sendMethods.concat tracker.find_call :targets => [:Socket,:TCPServer,:UDPSocket,:TCPSocket,:"Net::HTTP::Put",:"Net::HTTPGenericRequest",:"Net::HTTPRequest",:"Net::HTTP::Post"]
    sendMethods.concat tracker.find_call :targets => [:"Socket.new",:"TCPServer.new",:"UDPSocket.new",:"TCPSocket.new",:"Net::HTTP::Put.new",:"Net::HTTPGenericRequest.new",:"Net::HTTPRequest.new",:"Net::HTTP::Post.new",:"Net::HTTP.new"]




    

     sendMethods.each do |method|
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
    message = msg("File Send")

      warn :result => method,
        :warning_type => "File Send",
        :warning_code => :file_access,
        :message => message,
        :confidence => :high,
        :code => method[:call],
        :user_input => ""

  end


end
