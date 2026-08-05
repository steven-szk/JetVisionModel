#import serve
import sendESP

try:
    espcontrol = sendESP.sendESP()
    espcontrol.init()
    espcontrol.send_string("Initialise...")
    #serve.start_server(espcontrol)
except Exception as e:
    print(f"Error init: {e}")    
        
try:
    from capture import cap_frame, close_camera
    espcontrol.send_string("Camera Loaded")
except Exception as e:
    print(f"Error loading camera: {e}")
    
try:
    from infermodel import infer
    espcontrol.send_string("Models Loaded")
except Exception as e:
    print(f"Error loading models: {e}")
    


        
        
        
    
        
    




