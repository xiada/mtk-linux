import serial                                   
import time
import binascii
import struct
import sys

class MTKtools (object) :
  
  def __init__ (self) :
    
    #Preloader Download Commands
    self.CMD_GET_VERSION      = "\xff" #this returns echo if security is off i assume this to be the case for now !!!
    self.CMD_GET_BL_VER       = "\xfe"
    self.CMD_GET_HW_SW_VER    = "\xfc" 
    self.CMD_GET_HW_CODE      = "\xfd" 
    self.CMD_SEND_DA          = "\xd7" 
    self.CMD_JUMP_DA          = "\xd5" 
    self.CMD_GET_TARGE_CONFIG = "\xd8" 	
    self.CMD_READ16           = "\xa2" 
    self.CMD_WRITE16          = "\xd2" 
    self.CMD_READ32           = "\xd1" 
    self.CMD_WRITE32          = "\xd4" 
    self.CMD_PWR_INIT         = "\xc4" 
    self.CMD_PWR_DEINIT       = "\xc5" 
    self.CMD_PWR_READ16       = "\xc6" 
    self.CMD_PWR_WRITE16      = "\xc7"
    self.AGENT                = "MTK_AllInOne_DA.bin"
    self.AGENT_OFFSET         = 0x8280c
    self.BLOCK1_LENGTH        = 0x00ea6c
    self.BLOCK2_LENGTH        = 0x027530
    
  def split_by_n(self, seq, n ):
    """A generator to divide a sequence into chunks of n units."""
    while seq:
        yield seq[:n]
        seq = seq[n:]
        
  def open_serial (self,port) :
    
    timeout = time.time() + 10 #connection timeout 60 seconds   

    while True:
      if time.time() > timeout:
	return False
      try:
        self.ser = serial.Serial(port,19200, timeout=1)
	break
       
      except Exception, e:
        pass
      
    if not self.send_agent():
      return False
    else:
      return True 
    
  def read_rom (self,filename,start,length) :
    
    print "sending read mode"
    
    self.send_cmd("\x60\x08",2)
        
    self.send_cmd("\xd6\x0c\x02"+start+length,1)
  
    self.ser.write("\x00\x10\x00\x00")#just use it :D who cares why
         
    rom=""
    data=0;
    file = open(filename,'wb')
    
    while data<struct.unpack('>q',length)[0]:#data length
      datwrite=self.ser.read(0x400)
      if len(datwrite)==2 :#and datwrite=="\xca\xfe":
	 self.ser.write("\x5a")
      else:
        file.write(bytes(datwrite))
        sys.stdout.write('.')
	data+=0x400
    file.close()
    
    self.send_cmd("",2)
    print "sending 5a"
    self.send_cmd("\x5a",0)
    
  def send_cmd(self,cmd,res_length) :
    self.ser.write(cmd)
    res = self.ser.read(res_length)
    return res
    
 
  def send_agent(self) :
    
    while True:
      
      timeout = time.time() + 20 #connection timeout 60 seconds
     
      if time.time() > timeout:
	print "we have timed out"
        return False
     
      num_bytes=self.ser.inWaiting()
      data = self.ser.readline(num_bytes)
     
      if data=="READY":
        break
      
    print "sending token and start"
    self.send_cmd("\xa0\x00\x4b\x00\x00\x00\x00\x08\xa0\x0a\x50\x05",16)
    print "sending CMD_GET_HW_CODE"
    self.send_cmd(self.CMD_GET_HW_CODE,5)
    print "sending CMD_GET_HW_SW_VER"
    self.send_cmd(self.CMD_GET_HW_SW_VER,9)
    print "sending  CMD_READ32"
    self.send_cmd(self.CMD_READ32+"\x10\x00\x91\x70\x00\x00\x00\x01",17)
    print "sending CMD_WRITE32"
    self.send_cmd(self.CMD_WRITE32+"\x10\x00\x70\x00\x00\x00\x00\x01\x22\x00\x00\x00",17)
    print "sending CMD_GET_BL_VER"
    self.send_cmd(self.CMD_GET_BL_VER,1)
    print "sending ff"
    self.send_cmd(self.CMD_GET_VERSION,1)#this will echo id security off and i assume it is for now
    print "sending CMD_GET_BL_VER"
    self.send_cmd(self.CMD_GET_BL_VER,1)         
    print "sending CMD_SEND_DA fingers crossed "
    self.send_cmd(self.CMD_SEND_DA+"\x02\x00\x70\x00\x00\x00\xea\x6c\x00\x00\x01\x00",15)
    
    with open(self.AGENT, 'rb') as f:
      
           f.seek(self.AGENT_OFFSET)
           block1=f.read(self.BLOCK1_LENGTH)
           block2=f.read(self.BLOCK2_LENGTH)
           f.close()
           
    self.send_cmd(block1,4)
    print "sending CMD_JUMP_DA"
    self.send_cmd(self.CMD_JUMP_DA+"\x02\x00\x70\x00",48)#this response needs investigating

    print "sending 0x5a"#what is this Z maybe just a ready symbol
    self.send_cmd("\x5a",3)

    print "sending 0xff could be a sig."#what is this
    self.send_cmd("\xff\x01\x00\x08\x00\x70\x07\xff\xff\x01\x01\x50\x00\x00\x02\x01\x02\x00",2)

    self.send_cmd("\x80\x00\x00\x00\x00\x02\x75\x30\x00\x00\x10\x00",3)
    
    chunkstwo = list(self.split_by_n(block2,0x1000))   
    
    for i in range(0,len(chunkstwo)):
      print "Sending block2 chunk",i
      self.send_cmd(chunkstwo[i],1)

    self.send_cmd("",1)      
    print "sending 5a"  
    self.send_cmd("\x5a",232)
    self.send_cmd("",22)   

    print"send 72"
    self.send_cmd("\x72",2)
    print "send 72"
    self.send_cmd("\x72",2)

    return True


phone = MTKtools()

if phone.open_serial("/dev/ttyACM0") :
  print "connected"
  
  phone.read_rom("mybootrom.bin","\x00\x00\x00\x00\x02\x3a\x00\x00","\x00\x00\x00\x00\x00\xf0\x00\x00")
  phone.read_rom("myrecovery.bin","\x00\x00\x00\x00\x03\x2a\x00\x00","\x00\x00\x00\x00\x00\x5e\xd8\x00")

else:
  print "not connected"
