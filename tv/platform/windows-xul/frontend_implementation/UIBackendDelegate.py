import os
import subprocess
import resource
import webbrowser
import _winreg
import traceback
import ctypes

import prefs
import config
import dialogs
import frontend

currentId = 1
def nextDialogId():
    global currentId
    rv = currentId
    currentId += 1
    return rv

class UIBackendDelegate:
    openDialogs = {}

    def runDialog(self, dialog):
        id = nextDialogId()
        self.openDialogs[id] = dialog
        if isinstance(dialog, dialogs.ChoiceDialog):
            frontend.jsBridge.showChoiceDialog(id, dialog.title,
                    dialog.description, dialog.buttons[0].text,
                    dialog.buttons[1].text)
        elif isinstance(dialog, dialogs.HTTPAuthDialog):
            frontend.jsBridge.showHTTPAuthDialog(id, dialog.description)
        else:
            del self.openDialogs[id]
            dialog.runCallback(None)

    def handleDialog(self, dialogID, buttonIndex, *args, **kwargs):
        try:
            dialog = self.openDialogs.pop(dialogID)
        except KeyError:
            return
        if buttonIndex is not None:
            choice = dialog.buttons[buttonIndex]
        else:
            choice = None
        dialog.runCallback(choice, *args, **kwargs)

    def handleChoiceDialog(self, dialogID, buttonIndex):
        self.handleDialog(dialogID, buttonIndex)

    def handleHTTPAuthDialog(self, dialogID, buttonIndex, username, password):
        print "Username is (%s)" % username
        print "Password is (%s)" % password
        self.handleDialog(dialogID, buttonIndex, username=username, password=password)

    def dtvIsUpToDate(self):
        msg = '%s is up to date.' % config.get(prefs.LONG_APP_NAME)
        return

    def openExternalURL(self, url):
        # It looks like the maximum URL length is about 2k. I can't
        # seem to find the exact value
        if len(url) > 2047:
            url = url[:2047]
        try:
            webbrowser.open(url)
        except webbrowser.Error:
            util.failedExn("while opening %s in a new window" % url)

    def updateAvailableItemsCountFeedback(self, count):
        # Inform the user in a way or another that newly available items are
        # available
        # FIXME: When we have a system tray icon, remove that
        pass

    def notifyUnkownErrorOccurence(self, when, log = ''):
        frontend.jsBridge.showBugReportDialog(when, log)

    def copyTextToClipboard(self, text):
        frontend.jsBridge.copyTextToClipboard(text)

    # This is windows specific right now. We don't need it on other platforms
    def setRunAtStartup(self, value):
        if (value):
            filename = os.path.join(resource.resourceRoot(),"..","Democracy.exe")
            filename = os.path.normpath(filename)
            folder = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER,"Software\Microsoft\Windows\CurrentVersion\Run",0, _winreg.KEY_SET_VALUE)
            _winreg.SetValueEx(folder, "Democracy Player", 0,_winreg.REG_SZ, filename)
        else:
            folder = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER,"Software\Microsoft\Windows\CurrentVersion\Run",0, _winreg.KEY_SET_VALUE)
            _winreg.DeleteValue(folder, "Democracy Player")

    def killDownloadDaemon(self, oldpid):
        # Kill the old process, if it exists
        if oldpid is not None:
            # This isn't guaranteed to kill the process, but it's likely the
            # best we can do
            # See http://support.microsoft.com/kb/q178893/
            # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/347462
            PROCESS_TERMINATE = 1
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, oldpid)
            ctypes.windll.kernel32.TerminateProcess(handle, -1)
            ctypes.windll.kernel32.CloseHandle(handle)

    def launchDownloadDaemon(self, oldpid, env):
        self.killDownloadDaemon(oldpid)
        for key, value in env.items():
            os.environ[key] = value
        os.environ['DEMOCRACY_DOWNLOADER_LOG'] = \
                config.get(prefs.DOWNLOADER_LOG_PATHNAME)
        # Start the downloader.  We use the subprocess module to turn off the
        # console.  One slightly awkward thing is that the current process
        # might not have a valid stdin/stdout/stderr, so we create a pipe to
        # it that we never actually use.
        downloaderPath = os.path.join(resource.resourceRoot(), "..",
                "Democracy_Downloader.exe")
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.Popen(downloaderPath, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, 
                stdin=subprocess.PIPE,
                startupinfo=startupinfo)
