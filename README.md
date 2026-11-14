# Smart View with Google Cast on One UI 4.1 (Android 12)

Samsung removed Chromecast / Google Cast from Smart View in One UI 3 and brought it back only in Smart View 8.2.20.14 and newer, which ship with One UI 5.1+. Phones that ended on One UI 4.1, like the Galaxy S10, are stuck on Smart View 8.2.16.44, which cannot see Chromecasts at all.

This repository builds a Magisk module that replaces the stock Smart View with a patched 8.2.20.14, so Chromecast and other Google Cast devices show up in the normal Smart View list again.

**The Smart View APK is not included here.** It belongs to Samsung. You download it yourself and the build script patches your copy.

## Status

- Tested on one device: Galaxy S10 (SM-G973F), firmware `G973FXXSGHWC1`, Android 12, One UI 4.1, Magisk 31.
- Smart View starts, the UI works, and a Chromecast-type device is listed with the "Google Cast" label and can be used for mirroring.
- The flashable zip produced by `build.py` has the same contents as the module that was tested, but the zip install path itself was not tested. The tested module was created by hand in `/data/adb/modules`.
- Rarely used parts of Smart View (DeX, App Cast and so on) were not tested and may still hit Android 13 only APIs.

Use at your own risk. Removing the module brings the stock app back.

## Requirements

- Samsung phone on Android 12 (One UI 4.x) with stock Smart View in `/system/app/SmartMirroring`
- Root with Magisk 20.4 or newer
- Python 3 on a computer (no extra packages)

No LSPosed, no Frida.

## Build

1. Download **Samsung Smart View 8.2.20.14 (arm64-v8a) (Android 11+)** from APKMirror:
   <https://www.apkmirror.com/apk/samsung-electronics-co-ltd/samsung-smart-view/samsung-smart-view-8-2-20-14-release/samsung-smart-view-8-2-20-14-android-apk-download/>

   The file must have this SHA-256:

   ```
   0e2d8eeae64f0755558f4cb571498fc7465675ae84daada13c264af638461c19
   ```

2. Run the build script:

   ```bash
   python3 build.py com.samsung.android.smartmirroring_8.2.20.14-822000014_minAPI30*.apk
   ```

   It checks the SHA-256 of the input, patches the APK, checks the SHA-256 of the result and writes `smartview-googlecast-module.zip`.

   Expected SHA-256 of the patched APK:

   ```
   75842ce6be7fddff25490640c7b1c024edf693263c9826fb684214c394b1e065
   ```

## Install

1. Copy `smartview-googlecast-module.zip` to the phone and install it in the Magisk app (Modules, Install from storage).
2. Reboot. On devices where Magisk lives in the recovery partition (Galaxy S10 family), reboot into the Magisk system the usual way, for example `adb reboot recovery`.
3. Turn on Google Cast, using either way:
   - In Smart View: three dot menu, Settings, About Smart View, tap the words "Smart View" 10 times, enter the password `#00rtsp00`, enable **Google Cast**. This is the path described on XDA for 8.2.20.14; it was not the one used during testing.
   - With root (this is what was tested). Stop the app, add the line below before `</map>` in `/data/data/com.samsung.android.smartmirroring/shared_prefs/controller_ref_pref.xml`, keep the file owner and SELinux context:

     ```xml
     <boolean name="google_cast" value="true" />
     ```

4. Open Smart View. Cast devices on the same Wi-Fi appear in the list with the "Google Cast" label.

A side effect seen on the test device: Smart View was in English on the stock version because the Polish language pack on the phone was built for the newer app. With 8.2.20.14 the translation works again.

## Uninstall

Remove the module in Magisk and reboot.

## Why it is not just an APK update

- **Samsung blocks the install.** `adb install` of 8.2.20.14 on Android 12 fails with `INSTALL_FAILED_REJECTED_BY_BUILDTYPE` (-3001). The ASKS service rejects the APK because of the build token inside it. Placing the APK in `/system/app` through a Magisk module avoids the installer.
- **The app cannot be re-signed.** Smart View is signed with the Samsung platform key and needs signature permissions, so a rebuilt and re-signed APK would not work. The patches here are same-size edits inside `classes.dex`; the dex checksum and the zip CRC are fixed up and the APK Signing Block stays untouched. Packages scanned from the system partition have their certificates read without a full content check, so the original certificate still applies.
- **Android 13 APIs.** 8.2.20.14 was built for Android 13 and calls a few things Android 12 does not have.

## What gets patched

All offsets are inside `classes.dex` of the exact APK above.

| Offset | Change | Reason |
|---|---|---|
| `0x306CC4` | permission check returns `true` | The app requires `NEARBY_WIFI_DEVICES` on the Nearby Service package. That permission does not exist on Android 12, so the app would loop on a permission dialog forever. |
| `0x30706C` | call removed | `SemWifiP2pManager.unsetInUsePackage()` does not exist on Android 12 and crashes the app. |
| `0x30707C` | call removed | `SemWifiP2pManager.setInUsePackage()`, same as above. |
| `0x2BC798` | returns `false` | `SemWifiDisplay.isSupported("high_resolution_mode")` does not exist on Android 12. |

The Google Cast code in 8.2.20.14 uses the standard Android `MediaRouter` remote display routes served by Google Play services. That part of the system is still present and working on One UI 4.1, the stock Smart View simply never asks it to scan.

## Background

- XDA thread with the same problem on a Galaxy S10 and no solution: <https://xdaforums.com/t/question-update-smart-view-on-stock-rom.4577775/>
- XDA guide for the hidden Google Cast switch: <https://xdaforums.com/t/guide-how-to-enable-smartview-mirroring-on-chromecast-and-tv.4609351/>
