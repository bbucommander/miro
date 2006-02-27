import app
import frontend
import frontend_implementation
import os
import threading
import template
import util
import re

_genMutator = frontend_implementation.HTMLDisplay._genMutator
execChromeJS = frontend_implementation.HTMLDisplay.execChromeJS

###############################################################################
#### The Playback Controller                                               ####
###############################################################################

class PlaybackController (app.PlaybackControllerBase):
    
    def playItemExternally(self, itemID):
        item = app.PlaybackControllerBase.playItemExternally(self, itemID)
        # now play this item externally
        moviePath = ""
        try:
            moviePath = os.path.normpath(item.getPath())
            os.startfile(moviePath)
        except:
            print "DTV: movie %s could not be externally opened" % moviePath

###############################################################################
#### Right-hand pane video display                                         ####
###############################################################################

class VideoDisplay (app.VideoDisplayBase, frontend.HTMLDisplay):
    "Video player shown in a MainFrame's right-hand pane."

    def __init__(self):
        print "VideoDisplay init"
        html = template.fillStaticTemplate("video-display-vlc", {'eventCookie':self.getEventCookie(),'dtvPlatform':'xul'})
        frontend.HTMLDisplay.__init__(self,html)
        app.VideoDisplayBase.__init__(self)
        print "Display initialized"

    elapseRe = re.compile('elapsed=(\d+)')
    lengthRe = re.compile('len=(\d+)')

    # The mutation functions.
    videoPlay = _genMutator('videoPlay')
    videoPause = _genMutator('videoPause')
    videoReset = _genMutator('videoReset')
    videoStop = _genMutator('videoStop')
    videoFullscreen = _genMutator('videoFullscreen')
    videoSetVolume = _genMutator('videoSetVolume')
    videoSetRate = _genMutator('videoSetRate')
    videoSetPos = _genMutator('videoSetPos')

    def initRenderers(self):
        print "initRenderers"
        self.renderers.append(VLCPluginRenderer())

    def selectItem(self, item):
        print "VideoDisplay select item"
        self.itemPath = item.getFilename()
        app.VideoDisplayBase.selectItem(self, item)
 
    def play(self):
        print "VideoDisplay play %s" % self.itemPath
        app.VideoDisplayBase.play(self)
        url = util.absolutePathToFileURL(self.itemPath)
        self.videoPlay(url)

    def pause(self):
        print "VideoDisplay pause"
        app.VideoDisplayBase.pause(self)
        self.videoPause()

    def stop(self):
        print "VideoDisplay stop"
        self.videoStop()
        app.VideoDisplayBase.stop(self)
    
    def goFullScreen(self):
        print "VideoDisplay fullscreen"
        app.VideoDisplayBase.goFullScreen(self)
        self.videoFullscreen()

    def exitFullScreen(self):
        print "VideoDisplay exit fullscreen"
        app.VideoDisplayBase.exitFullScreen(self)

    def setVolume(self, level):
        print "VideoDisplay set volume %s" % level
        app.VideoDisplayBase.setVolume(self, level)
        self.videoSetVolume(str(level))

    def setRate(self, rate):
        print "VideoDisplay set rate %s" % rate
        #app.VideoDisplayBase.setRate(self, rate)
        self.videoSetRate(str(rate))

    def muteVolume(self):
        print "VideoDisplay mute volume"
        app.VideoDisplayBase.muteVolume(self)

    def restoreVolume(self):
        print "VideoDisplay restore volume"
        app.VideoDisplayBase.restoreVolume(self)

    def onSelected(self, frame):
        print "VideoDisplay on selected"
        app.VideoDisplayBase.onSelected(self, frame)

        # Reset the display so it can be reused
        html = template.fillStaticTemplate("video-display-vlc", {'eventCookie':self.getEventCookie(),'dtvPlatform':'xul'})

        frontend_implementation.HTMLDisplay.pendingDocuments[self.getEventCookie()] = ("text/html", html)

	frontend_implementation.HTMLDisplay.HTMLDisplay.cookieToInstanceMap[self.eventCookie] = self

        self.mutationOutput = None
        self.queue = []

    def onDeselected(self, frame):
        print "VideoDisplay deselected"
        app.VideoDisplayBase.onDeselected(self, frame)

    def onURLLoad(self, url):
        print "DTV video: %s" % url
        # FIXME we probably should have some sort of a controller here
        if ("action:videoPlayPause" == url):
            self.playbackController.playPause()
            return False
        elif ("action:videoFullscreen" == url):
            self.goFullScreen()
            return False
        elif ("action:videoStop" == url):
            self.playbackController.stop()
            return False
        elif ("action:videoNext" == url):
            self.playbackController.skip(1)
            return False
        elif ("action:videoPrev" == url):
            self.playbackController.skip(-1)
            return False
        elif (url.startswith("action:setVolume?level=")):
            self.setVolume(float(url[23:]))
            return False
        elif (url.startswith("action:setRate?rate=")):
            self.setRate(float(url[20:]))
            return False
        elif (url.startswith("action:enableVideoControls")):
            execChromeJS('videoEnableControls();')
            return False
        elif (url.startswith("action:disableVideoControls")):
            execChromeJS('videoDisableControls();')
            return False
        elif (url.startswith("action:setVideoProgress?pos=")):
            self.videoSetPos(url[28:])
            return False
        elif (url.startswith("action:updateVideoControls?")):
            elapsed = self.elapseRe.search(url).group(1)
            length = self.lengthRe.search(url).group(1)
            execChromeJS('videoProgressUpdate(%s, %s);' % (elapsed, length))
        return True

class VLCPluginRenderer (app.VideoRenderer):

    def __init__(self):
        app.VideoRenderer.__init__(self)
        print "Renderer initialized"

    def reset(self):
        print "Renderer reset"

    def canPlayItem(self, item):
        print "canPlayItem"
        return True

    def selectItem(self, item):
        print "Renderer select item"
        self.itemPath = item.getFilename()

    def play(self):
        print "Renderer play"

    def pause(self):
        print "Renderer pause"

    def stop(self):
        print "Renderer stop"

    def goToBeginningOfMovie(self):
        print "Renderer go to beginning"

    def getDuration(self):
        print "Renderer getDuration"
        return 0

    def getCurrentTime(self):
        print "Renderer getCurrentTime"
        return 0

    def setCurrentTime(self, time):
        print "Renderer Set current time"

    def getRate(self):
        print "Renderer get rate"
        return 0.0

    def setRate(self, rate):
        print "Renderer set rate"
        
    def setVolume(self, level):
        print "Renderer set volume %s" % level

###############################################################################
#### Playlist item base class                                              ####
###############################################################################

class PlaylistItem:
    "The record that makes up VideoDisplay playlists."

    def getTitle(self):
        """Return the title of this item as a string, for visual presentation
        to the user."""
        raise NotImplementedError

    def getPath(self):
        """Return the full path in the local filesystem to the video file
        to play."""
        raise NotImplementedError

    def getLength(self):
        """Return the length of this item in seconds as a real number. This
        is used only cosmetically, for telling the user the total length
        of the current playlist and so on."""
        raise NotImplementedError

    def onViewed(self):
        """Called by the frontend when a clip is at least partially watched
        by the user. To handle this event, for example by marking the
        item viewed in the database, override this method in a subclass."""
        raise NotImplementedError

###############################################################################
###############################################################################
