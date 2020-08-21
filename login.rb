require 'paho-mqtt'
require 'json'
$hscn_sub = "homie/trumpy_bear/screen/control/set"
$hscn_pub = "homie/trumpy_bear/screen/control"
$hcmd_pub = "homie/trumpy_bear/control/cmd/set"
$hdspm_sub = 'homie/trumpy_ranger/display/mode/set'
$hdspt_sub = 'homie/trumpy_ranger/display/text/set'

Shoes.app do 
  
  stack do
    @hdr = tagline "Trumpy Bear"
    @msg = tagline "Login/Registration"
    @panel = stack do
      @img = image '/var/www/camera/face.jpg', height: 300, width: 280, cache: false
    end
    flow do 
      @login_btn = button "Login" do 
        login
      end
      @alarm_btn = button "Alarm" do
        # how to turn off ?
      end
      @voice_btn = button "Voice" do
        # mycroft conversation(s) Lasers.
      end
      @lasers_btn = button "Lasers" do
      end
    end # buttons flow
  end # top level stack
  start {
    $client = PahoMqtt::Client.new({persistent: true, keep_alive: 7, client_id: 'TB Login App'})
    $client.connect("192.168.1.7", 1883)
    $client.on_message { |msg|
      debug "#{msg.topic} #{msg.payload}"
      if msg.topic == $hscn_sub 
        if msg.payload == 'wake'
          wake_up
        else
          hsh = JSON.parse(msg.payload)
          debug "json parse: #{hsh.inspect}"
          cmd =  hsh['cmd']
          if cmd == 'wake'
            wake_up
          elsif cmd == 'register'
            do_register
          elsif cmd == 'user'
            @img.path = '/var/www/camera/face.jpg'
            user = hsh['user']
            role = hsh['role']
            debug "#{user} logged in"
            @msg.text = "#{user} is logged in"
            @alarm_btn.show
            @voice_btn.show
            @lasers_btn.show
          elsif cmd == 'logout'
            @alarm_btn.hide
            @voice_btn.hide
            @lasers_btn.hide
            @msg.text = 'Login'
          end
        end
      elsif msg.topic == $hdspm_sub
        # mode command. 
        # if 'off' - sleep monitor else wake it up
        
      elsif msg.topic == $hdspt_sub
        # text command
        @msg.text = msg.payload
      end
    }
    $client.subscribe([$hscn_sub, 1], [$hdspm_sub, 1], [$hdspt_sub, 1]) 
    #$client.subscribe($hscn_sub)
    Thread.new do
      $client.loop_read
      sleep 0.1
    end
    @alarm_btn.hide
    @voice_btn.hide
    @lasers_btn.hide
    debug "start block"
  }
  
  def wake_up
    # run Hubitat automations 
    debug "Wake up runs"
    $client.publish($hscn_pub, "awake", false, 1)
  end
  
  def do_register
    # tell hubitat we are working.
    wake_up
    # put Trumpybear in Register Mode
    dt = {'cmd': 'register'}
    $client.publish($hcmd_pub,dt.to_json)
    @msg.text = 'Requesting Login'
  end
  
  def login
    dt = {'cmd': 'login'}
    $client.publish($hcmd_pub,dt.to_json)
  end

end
