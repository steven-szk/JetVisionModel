#import serve
import sendESP

try:
    espcontrol = sendESP.sendESP()
    espcontrol.init()
        
    #serve.start_server(espcontrol)
except Exception as e:
    print(f"Error init: {e}")    
        
try:
    espcontrol.send_string("Loading Camera")
    from capture import cap_frame, close_camera
except Exception as e:
    print(f"Error loading camera: {e}")
    
try:
    espcontrol.send_string("Loading Models")
    from infermodel import infer
except Exception as e:
    print(f"Error loading models: {e}")
    


        
        
        
    
        
    




