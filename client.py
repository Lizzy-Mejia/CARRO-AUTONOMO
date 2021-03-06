import RPi.GPIO as GPIO
import time
import io
import socket
import struct
import picamera
import threading

# Configure Raspberry Pi GPIO in BCM mode
GPIO.setmode(GPIO.BCM) 


# Config vars. These IP and ports must be available in server firewall
log_enabled = True
server_ip = '192.168.1.20'
server_port_ultrasonic = 8001
server_port_camera = 8000

# Camera configuration
image_width = 640
image_height = 480
image_fps = 10
recording_time = 600

# Ultrasonic sensor configuration
ultrasonic_sensor_enabled = True

# Definition of GPIO pins in Raspberry Pi 3 (GPIO pins schema needed!)
#   18 - Trigger (output)
#   24 - Echo (input)
GPIO_ultrasonic_trigger = 18
GPIO_ultrasonic_echo = 24


print('PROYECTO UMG CARRO AUTONOMO')
print('7690-07-2496 Edy Mora')
print('7690-13-7664 Adderly Sinay')
print('7690-16-9699 Jose Garcia')
print('7690-16-10388 Elizabeth Mejia')
print('7690-16-3583 Hermes Sotoj')
# Class to handle the ultrasonic sensor stream in client
class StreamClientUltrasonic():

    def measure(self):
        
        GPIO.output( GPIO_ultrasonic_trigger, True )
        time.sleep( 0.00001 )
        GPIO.output( GPIO_ultrasonic_trigger, False )
        

        start = time.time()

        while GPIO.input( GPIO_ultrasonic_echo ) == 0:
            start = time.time()
            
        while GPIO.input( GPIO_ultrasonic_echo ) == 1:
            stop = time.time()

        time_elapsed = stop-start
        distance = (time_elapsed * 34300) / 2

        return distance

  
    def __init__(self):

        # Connect a client socket to server_ip:server_port_ultrasonic
        print( '+ Conectando al servidor del sensor Ultrasonico ' + str( server_ip ) + ':' + str( server_port_ultrasonic ) );

        # Configure GPIO pins (trigger as output, echo as input)
        GPIO.setup( GPIO_ultrasonic_trigger, GPIO.OUT )
        GPIO.setup( GPIO_ultrasonic_echo, GPIO.IN )

        # Set output GPIO pins to False
        GPIO.output( GPIO_ultrasonic_trigger, False ) 

        # Create socket and bind host
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect( ( server_ip, server_port_ultrasonic ) )

        try:
            while True:
                # Measure and send data to the host every 0.5 sec, 
                # pausing for a while to no lock Raspberry Pi processors
                distance = self.measure()
                if log_enabled: print( "Distancia: %.1f cm" % distance )
                client_socket.send( str( distance ).encode('utf-8') )
                time.sleep( 0.5 )

        finally:
            # Ctrl + C to exit app (cleaning GPIO pins and closing socket connection)
            print( 'Conexion con el sensor fue desconectada' );
            client_socket.close()
            GPIO.cleanup()


# Class to handle the jpeg video stream in client
class StreamClientVideocamera():
  
    def __init__(self):

        # Connect a client socket to server_ip:server_port_camera
        print( '+ Iniciando conexion con Servidor de Video en: ' + str( server_ip ) + ':' + str( server_port_camera ) );

        # create socket and bind host
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((server_ip, server_port_camera))
        connection = client_socket.makefile('wb')

        try:
            with picamera.PiCamera() as camera:
                camera.resolution = (image_width, image_height)
                camera.framerate = image_fps

                # Give 2 secs for camera to initilize
                time.sleep(2)                       
                start = time.time()
                stream = io.BytesIO()
                
                # send jpeg format video stream
                for foo in camera.capture_continuous(stream, 'jpeg', use_video_port = True):
                    connection.write(struct.pack('<L', stream.tell()))
                    connection.flush()
                    stream.seek(0)
                    connection.write(stream.read())
                    if time.time() - start > recording_time:
                        break
                    stream.seek(0)
                    stream.truncate()
            connection.write(struct.pack('<L', 0))

        finally:
            connection.close()
            client_socket.close()
            print( 'Stream de conexion ha sido cancelada' );

 

# Class to handle the different threads in client 
class ThreadClient():

    # Client thread to handle the video
    def client_thread_camera(host, port):
        print( '--Iniciando conexion de Streaming ' + str( host ) + ':' + str( port ) )
        StreamClientVideocamera()

    # Client thread to handle ultrasonic distances to objects
    def client_thread_ultrasonic(host, port):
        print( '--Iniciando conexion con Sensor Ultrasonico' + str( host ) + ':' + str( port ) )
        StreamClientUltrasonic()

    if ultrasonic_sensor_enabled:
        thread_ultrasonic = threading.Thread( name = 'thread_ultrasonic', target = client_thread_ultrasonic, args = ( server_ip, server_port_ultrasonic ) )
        thread_ultrasonic.start()
    
    thread_videocamera = threading.Thread( name = 'thread_videocamera', target = client_thread_camera, args = ( server_ip, server_port_camera ) )
    thread_videocamera.start()


# Starting thread client handler
if __name__ == '__main__':
    ThreadClient()
