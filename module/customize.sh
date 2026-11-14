# Runs inside the Magisk module installer.

if [ "$API" != "31" ]; then
  abort "! This module is for Android 12 (API 31) only, this device is API $API"
fi

if [ ! -f /system/app/SmartMirroring/SmartMirroring.apk ]; then
  abort "! /system/app/SmartMirroring/SmartMirroring.apk not found, not a supported One UI 4.1 build"
fi

set_perm_recursive "$MODPATH/system" 0 0 0755 0644

# The compiled code of the stock app does not match the new APK.
rm -f /data/dalvik-cache/*/system@app@SmartMirroring@SmartMirroring.apk@classes.*

ui_print "- Reboot, then turn on Google Cast in Smart View (see README)"
