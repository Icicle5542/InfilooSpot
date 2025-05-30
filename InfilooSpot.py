#spotify
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# mpc / mpd
# from mpd import MPDClient

# UI
import lcddriver
from evdev import InputDevice, categorize, ecodes, list_devices

#system 
import os
from _thread import start_new_thread
from threading import Thread, Lock

#debug and misc
from pprint import pprint
from time import sleep
from enum import Enum
import json

# Find the first keyboard device
def find_keyboard():
    print(list_devices())
    for dev_path in list_devices():
        dev = InputDevice(dev_path)
        print(f"iterating device: {dev.name} at {dev.path}")
        if '/dev/input/event0' in dev.path:
            print(f"Found keyboard device: {dev.name} at {dev.path}")
            return dev
    # fallback: just return the first device
    print("No keyboard device found, using the first available device.")
    print(f"Using device: {list_devices()[0]}")
    return InputDevice(list_devices()[0])

keyboard_dev = find_keyboard()

# general operation mode
class GMode(Enum):
    NONE    = 0             # startup - not yet initialized
    SPOT    = 1             # spotify
    IRAD    = 2             # mpd internetradio
    MED     = 3             # mpd media
    EXIT    = 10            # stop all

gmode       = GMode.NONE    # start with blank and wait until the init is done to switch to SPOT 

HelloShown = False          # show some start only when starting for the 1st time and not when we loop
Exit       = False          # we really want to get out
Paused     = False          # true when we used pause to stop

playlists  = []             # the users playlists when fetched after command p
playlistidx = 0             # idx when iterating through th eplaylists

albums     = []             # when we looked for an album this is the list to iterate through
albumidx   = 0              # current selected album


# change general mode
def change_gmode(new_mode):
    global gmode

    print("change mode to: "  + new_mode.name)
    try:
        if(new_mode == GMode.SPOT):
            print("SPOT")
            sp.start_playback()         # go on playing
            # mpc.stop();                 # stop playing with mpc
            # mpc.clear()

        elif(new_mode == GMode.IRAD):
            print("IRAD")
            sp.pause_playback()         # stop playing spotify
            # mpc.stop();                 # stop playing with mpc
            # mpc.clear()

        elif(new_mode == GMode.MED):
            print("MED")
            sp.pause_playback()         # stop playing spotify
            # mpc.stop();                 # stop playing with mpc
            # mpc.clear()

        elif(new_mode == GMode.EXIT):
            print("EXIT")
            sp.pause_playback()         # stop playing spotify
            # mpc.stop();                 # stop playing with mpc
            # mpc.clear()

    except:
        print("Ups in changemode")
    
    gmode = new_mode

            
# a background task fetching the current playback and showing it at the 2nd line of the display
def show_current_playback():
    global sp
    
    while True:
        try:
            if gmode == GMode.SPOT:
                x = sp.current_playback("DE")
                if((x != None) and (any(x))):
                    it = x.get("item")
                    if(any(it)):
                        # print(json.dumps(it, indent=4))     # get a full formatted output of what spitify gives us

                        if(Paused == False):
                            # show title in the 2nd row
                            tit = it["name"]
                            if(any(tit)):
                                printlcd(0, 1, tit)

                            # show album
                            alb = it["album"]["name"]
                            if(any(alb)):
                                printlcd(0, 2, alb)

                            # show 1st artist
                            art = it["artists"][0]["name"]
                            if(any(alb)):
                                printlcd(0, 3, art)
                        else:
                            printlcd(0, 1, "   *** paused ***")
                            printlcd(0, 2, "")
                            printlcd(0, 3, "")

            elif (gmode == GMode.IRAD) or (gmode == GMode.MED):
                # cursong = mpc.currentsong()
                if(any(cursong)):
                    # print(json.dumps(cursong, indent=4))     # get a full formatted output of what spitify gives us
                    print(cursong)

                    # show station name
                    stname = ""
                    if("name" in cursong.keys()):
                        # print(cursong["name"])
                        stname = cursong["name"]
                        printlcd(0, 1, cursong["name"])
                    else:
                        printlcd(0, 1, "")

                    # show title (if given and different from name (as some stations send it)
                    if("title" in cursong.keys() and (stname != cursong["title"])):     
                        # print(cursong["name"])
                        printlcd(0, 2, cursong["title"])
                    else:
                        printlcd(0, 2, "")

                    # clear 4th line
                    printlcd(0, 3, "")
                        
        except:
            print("Ups in show playback")

        sleep(2)


lcd_mutex = Lock()                      # use this mutex to lock the diplay access

# function to write to the display using the mutex to avoid reentrance issues
def printlcd(x, y, str):
    lcd_mutex.acquire()
    lcd.lcd_display_string((str + "                    ")[:20], y + 1) # right fill the complete display line but cut everything that is outside of the diasplay
    lcd_mutex.release()

# change the alsa colume up or down by a given % value
def change_volume(volume):
    global currentvol
    global sp

    try:
        # print("Volume(1): " + str(currentvol))
        if ((currentvol + volume) <= 100) and ((currentvol + volume) >= 0):
            currentvol = currentvol + volume
            # mpc.setvol(currentvol)
            x = sp.current_playback("DE")                       # spotipy crashes when volume() is called but it is not playing yet
            if((x != None) and (any(x))):
                sp.volume(currentvol)
            print("Volume: " + str(currentvol))
            printlcd(0, 0, "Volume: " + str(currentvol) + "%")
    except:
        print("Ups in change_volume")

def get_key_cmd():
    """
    Reads key events from the keyboard device and returns the command string.
    Handles special keys for navigation and volume.
    """
    cmd = ''
    # print("read_loop ...")
    for event in keyboard_dev.read_loop():
        # print("read_loop ...")
        if event.type == ecodes.EV_KEY:
            key_event = categorize(event)
            if key_event.keystate == key_event.key_down:
                keycode = key_event.keycode

                # Map special keys to commands
                if keycode in ['KEY_ENTER']:
                    return cmd
                elif keycode in ['KEY_BACKSPACE']:
                    cmd = cmd[:-1]
                    printlcd(0, 0, cmd)
                elif keycode in ['KEY_SPACE']:
                    cmd += ' '
                    printlcd(0, 0, cmd)
                elif keycode in ['KEY_LEFT']:
                    return 'p'
                elif keycode in ['KEY_RIGHT']:
                    return 'n'
                elif keycode in ['KEY_UP', 'KEY_VOLUMEUP']:
                    return 'u'
                elif keycode in ['KEY_DOWN', 'KEY_VOLUMEDOWN']:
                    return 'd'
                elif keycode in ['KEY_PLAYPAUSE']:
                    return '#'
                else:
                    # Handle normal character keys
                    if isinstance(keycode, list):
                        keycode = keycode[0]
                    if keycode.startswith('KEY_'):
                        char = keycode[4:].lower()
                        # Swap y/z for German keyboards
                        if char == 'z':
                            cmd += 'y'
                        elif char == 'y':
                            cmd += 'z'
                        elif len(char) == 1:
                            cmd += char
                        printlcd(0, 0, cmd)


################################################################################################
# start background thread to show what we are doing
start_new_thread(show_current_playback, ())

# wrap it all in an endless loop to try again if it fails
while Exit == False:
    try:
        if HelloShown == False:
            HelloShown = True

            # lcd start
            lcd = lcddriver.lcd()
            lcd.lcd_clear()

            print("Hello at InfilooSpot!")   
            printlcd(0, 0, "  InfilooSpot!")

        # run through init which seems to fail especially when wifi is bad or takes longer to establish
        bInitDone = False
        while bInitDone == False:
            try:
                printlcd(0, 1, "  _-_-_-_-_-_")

                # init and connect to spotify
                print("Init spotify...")
                sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                    client_id="680ca5403c694cac9f37b459353cbaeb",
                    client_secret="bb988ada317e44e9a1a73f0b7accf06c",
                    redirect_uri="http://127.0.0.1:8888/callback",  # Use a port, e.g., 8888
                    scope="user-read-playback-state,user-modify-playback-state,playlist-read-private",
                    username="n9wfeceo0a5c0kytomcrpiu2w",
                    cache_path="/home/icicle/Documents/InfilooSpot/InfilooSpot/.cache-spotipy",
                    open_browser=False  # <--- Add this to avoid that a browser is opened. instead it will print the URL to open on another PC
                ))
                # Shows playing spotify connect devices
                print("Show devices ...")
                res = sp.devices()
                pprint(res)
                printlcd(0, 1, "  _-_-_-_-_-_S")

                # set volume back to normal
                currentvol = 50
 
                bInitDone = True
                print("Init done")

            except: 
                print("Ups in init")
                sleep(1)
        
        gmode = GMode.SPOT
        cmd   = ' '
        typec = ''

        print("run main loop...")
        while (cmd != 'q') and (cmd != 'e'):
            # Collect key characters until released - which will happen when enter is pressed
            cmd = ''                    #  clear cmd, finally we will find the new cmd here
            print(" cmdget_key_cmd ...")
            cmd = get_key_cmd()
            print(" cmd: " + cmd)

            if cmd == '1':
                print("all")
                printlcd(0, 0, "  all")
                change_gmode(GMode.SPOT)
                typec = ''
                playlists  = []             
                albums     = []
         
            elif cmd == '2':
                print("artist")
                printlcd(0, 0, "  artist")
                change_gmode(GMode.SPOT)
                typec = 'artist'
                playlists  = []             
                albums     = []

            elif cmd == '3':
                print("album")
                printlcd(0, 0, "  album")
                change_gmode(GMode.SPOT)
                typec = 'album'
                playlists  = []             
                albums     = []
                
            elif cmd == '4':
                print("track")
                printlcd(0, 0, "  track")
                change_gmode(GMode.SPOT)
                typec = 'track'
                playlists  = []             
                albums     = []

            elif cmd == '5':
                print("playlist")
                printlcd(0, 0, "  playlist ...")
                change_gmode(GMode.SPOT)
                albums      = []
                playlists   = sp.current_user_playlists(50, 0)        # fetch playlists from user account
                # playlistidx = 0                                     # keep the idx so we start with the list used at the time selection
                for idx, item in enumerate(playlists['items']):
                    print(idx, item['name'] + " - " + item["id"])
                printlcd(0, 0, "P " + playlists["items"][playlistidx]["name"])


            elif cmd == 'q':
                print("goodbye")
                printlcd(0, 0, "  InfilooSpot!  ")
                printlcd(0, 1, "   shutdown     ")
                change_gmode(GMode.EXIT)

                os.system("sudo shutdown now")
                break

            elif cmd == 'e':
                print("exit")
                printlcd(0, 0, "  InfilooSpot!  ")
                printlcd(0, 1, "      exit      ")
                change_gmode(GMode.EXIT)

                Exit = True
                exit()
                break

            elif cmd == "u":
                print("VolUp")
                change_volume(5)

            elif cmd == "d":
                print("VolDown")
                change_volume(-5)

            elif cmd == 'n':
                print("next")
                if gmode == GMode.SPOT:
                    if any(playlists):                  # when the list is not empty we are in playlist mode
                        if(len(playlists["items"]) > (playlistidx + 1)):
                            playlistidx += 1
                            printlcd(0, 0, "P " + playlists["items"][playlistidx]["name"])

                    elif any(albums):
                        if(len(albums["albums"]["items"]) > (albumidx + 1)):
                                albumidx += 1
                                printlcd(0, 0, "A " + albums["albums"]["items"][albumidx]["name"])    # show album

                    else:
                        sp.next_track()

            elif cmd == 'p':
                print("previous")
                if gmode == GMode.SPOT:
                    if any(playlists):                  # when the list is not empty we are in playlist mode
                        if(playlistidx >= 1):
                            playlistidx -= 1
                            printlcd(0, 0, "P " + playlists["items"][playlistidx]["name"])

                    elif any(albums):                  # when the list is not empty we are in playlist mode
                        if(albumidx >= 1):
                            albumidx -= 1
                            printlcd(0, 0, "A " + albums["albums"]["items"][albumidx]["name"])    # show album
                        
                    else:
                        sp.previous_track()

            elif cmd == "#":
                if(Paused == False):
                    Paused = True
                    print("pause")
                    sp.pause_playback('eeb73d9d5a4e47863facfa09d65f0170263e30d1')
                else:
                    Paused = False
                    print("resume")
                    sp.start_playback('eeb73d9d5a4e47863facfa09d65f0170263e30d1')


            elif cmd == '':                         # no input - in playlist mode selection if current playlist
                print("select")
                if any(playlists):                  #  when we have a selected playlist ask spotify to play it
                    sp.start_playback('eeb73d9d5a4e47863facfa09d65f0170263e30d1', playlists["items"][playlistidx]["uri"]) 

                    playlists  = []                 # back to normal mode now playing the playlist
                    # playlistidx = 0               # keep idx so we start from this in the list next time            

                elif any(albums):                   # when we have a selected album ask spotify to play it 
                    sp.start_playback('eeb73d9d5a4e47863facfa09d65f0170263e30d1', albums['albums']["items"][albumidx]["uri"])

                    albums   = []                   # select list to return int normal mode
                    albumidx = 0
                            

            else:
                # only when we have a string to search for
                if cmd != '':
                    # when typec is not empty construct the query
                    if typec != '':
                        cmd = typec + ":" + cmd
                        print(cmd)
                    
                    if(typec != 'album'):
                        # search it if it is just a normal search request for a track
                        results = sp.search(q = cmd, limit = 50)

                        # check if there is anything at all
                        if(any(results)):
                            trackURIs = []
                            for idx, track in enumerate(results['tracks']['items']):
                                print(idx, track['name'], track['uri'] )
                                trackURIs.append(track['uri'])
                    
                            sp.start_playback('eeb73d9d5a4e47863facfa09d65f0170263e30d1', uris=trackURIs)      

                    else:
                        # look for albums and generate a list of found ones to select like a playlist
                        albums   = sp.search(cmd, limit = 50, type = "album")
                        albumidx = 0
                        printlcd(0, 0, "A " + albums["albums"]["items"][albumidx]["name"])    # show 1st album

    except:
        if Exit == False:
            print("Ups")


