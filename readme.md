# 📦 BunAPK

Download Android apps straight from the Google Play Store, right from your command line.

No Google account needed. No sign-in. Just type the app's name and BunAPK grabs it for you.

```bash
bunapk com.example.app
```

<br>

## 🤔 What is this?

When you install an app from the Play Store, Google doesn't hand you one neat file. It quietly sends your phone a bunch of smaller pieces, picked for your exact device.

**BunAPK collects all of those pieces for you** and bundles them into a single file you can install yourself (called an `.apks` file).

You might want this if you:

- 💾 Want to keep a backup copy of an app
- 📴 Need to install an app on a device with no Play Store
- 🕹️ Want an older version of an app

That's it. You give it an app's package name, it gives you a file.

<br>

## 🆚 A free alternative to APKMirror, APKPure & APKCombo

If you've ever used **APK archive sites** like APKMirror, APKPure, or APKCombo to download an APK, BunAPK does the same job — but better, and right from your terminal.

Here's why people use it for **archiving and backing up their favorite apps**:

- 🧩 **You get the complete app, not a half one.** BunAPK downloads *every* piece — all CPU types (arm64 and armeabi-v7a), all screen sizes, and all languages — and bundles them into one `.apks` file. A lot of archive sites only give you a partial or incomplete bundle. BunAPK doesn't.

- 🕰️ **You can get old versions.** Many archive sites quietly delete older versions over time. With BunAPK you can pull a specific older version straight from Google Play, so the version you need doesn't just disappear.

- 🆓 **No ads, no waiting, no sketchy "Download" buttons.** It comes straight from Google Play using anonymous access — no account, no login.

- 🗄️ **Perfect for keeping your own app library.** Save clean, complete copies of the apps you care about so you always have them, even if they get pulled from the store later.

In short: if you want a **reliable way to download and archive full Android app bundles**, BunAPK is built exactly for that. 💪

<br>

## ✅ Before you start

You only need two things:

1. **Python 3.9 or newer** installed on your computer or phone
2. **An internet connection**

The installation steps below will help you get Python if you don't have it yet.

<br>

## 💻 Installing BunAPK

Pick the section for your device. Follow it top to bottom.

When you're done, test it by running:

```bash
bunapk --help
```

If you see a help screen, you're good to go. 🎉

<br>

### 🍎 Mac & Linux

On Mac and modern Linux, installing Python tools the "normal" way often throws a confusing error (`externally-managed-environment`).

To skip that headache completely, we use a friendly tool called **pipx**. It installs BunAPK in its own little space and automatically makes the `bunapk` command work everywhere.

**Step 1 — Install pipx**

On Mac (using [Homebrew](https://brew.sh)):

```bash
brew install pipx
```

On Linux:

```bash
sudo apt install pipx
```

**Step 2 — Let pipx set up your PATH (do this once)**

```bash
pipx ensurepath
```

👉 Now **close your terminal and open a new one.** This makes the change take effect.

**Step 3 — Install BunAPK**

```bash
pipx install git+https://github.com/UltraMotionOfficial/BunAPK.git
```

Done! ✨

> 💡 Later on, you can update to the newest version with:
> ```bash
> pipx upgrade bunapk
> ```

<br>

### 🪟 Windows

**Step 1 — Install Python**

Download it from [python.org/downloads](https://www.python.org/downloads/).

⚠️ **This part is super important:** on the very first screen of the installer, check the box that says **"Add python.exe to PATH"** before you click Install.

If you skip that box, the `bunapk` command won't work. (No worries if you missed it — just run the installer again, choose **Modify**, and tick the box.)

**Step 2 — Open a new Command Prompt and install BunAPK**

```bash
pip install git+https://github.com/UltraMotionOfficial/BunAPK.git
```

Done! ✨

<br>

### 🤖 Android (Termux)

You'll use the free **Termux** app (a terminal for Android).

**Step 1 — Set up storage and keep Termux awake FIRST**

```bash
termux-setup-storage && termux-wake-lock
```

📲 Your phone will pop up a permission box — tap **Allow**.

This one line does two important things:

- 📂 **`termux-setup-storage`** lets BunAPK save your downloads into a folder you can actually find later.
- 🔋 **`termux-wake-lock`** keeps the download running even if you minimize Termux or switch to other apps. Without it, Android can pause Termux in the background and interrupt your download.

**Step 2 — Install Python and Git**

```bash
pkg update && pkg upgrade -y
pkg install python git -y
```

**Step 3 — Install BunAPK**

```bash
pip install git+https://github.com/UltraMotionOfficial/BunAPK.git
```

Done! ✨

> 💡 If typing `bunapk` ever says "command not found", just use `python -m bunapk` instead. It does the exact same thing.

<br>

## 🚀 How to use it

There are really just three things you can do.

<br>

### ⬇️ Download an app

This is the main one. Type `bunapk` followed by the app's package name:

```bash
bunapk com.example.app
```

BunAPK will grab all the pieces and save one finished file for you.

> ❓ **What's a "package name"?**
> It's the app's unique ID, and it always looks like a website address in reverse, for example `com.example.app`.
>
> Not sure what it is? The **search** command below will find it for you.

<br>

### 🔍 Find an app (search)

Don't know an app's package name? Search for it by its normal name:

```bash
bunapk search "photo editor"
```

You'll get a list of matching apps and their package names. Then just copy the package name and use it to download.

By default you'll see up to **10** results. Want a shorter list? Use `-l` (short for "limit") with a number to cap how many you get:

```bash
bunapk search "photo editor" -l 5
```

<br>

### ℹ️ Check an app's details (info)

Want to peek at an app before downloading it? Use **info**:

```bash
bunapk info com.example.app
```

This shows you the app's name, version, developer, rating, and how many downloads it has.

<br>

## 📁 Where do my files go?

BunAPK saves your downloads into a folder called **BunAPK**, in the normal place for your device:

| Your device | Where files are saved |
| :--- | :--- |
| 🤖 Android (Termux) | Your phone's main storage → `BunAPK` |
| 🍎 Mac / Linux | `Downloads/BunAPK` |
| 🪟 Windows | `Downloads\BunAPK` |

Don't worry about creating the folder — BunAPK makes it for you automatically.

<br>

### Want a different folder name?

Add `-o` and a name. BunAPK keeps it **inside your Downloads folder**, so your files never end up lost in some random place:

```bash
bunapk com.example.app -o FolderName
```

| Your device | Where this goes |
| :--- | :--- |
| 🤖 Android (Termux) | Your phone's main storage → `FolderName` |
| 🍎 Mac / Linux | `Downloads/FolderName` |
| 🪟 Windows | `Downloads\FolderName` |

> 🛟 Want it somewhere completely different instead? Just give a **full path** (like `/storage/emulated/0/Download/apps` on Android, `~/Desktop/apps` on Mac, or `D:\Apps` on Windows) and BunAPK will use exactly that.

<br>

## 📲 How do I install the file on my phone?

The file you get is an `.apks` file. It holds several pieces, so a regular tap-to-install won't work. You need a small helper app.

The easiest one is **SAI (Split APKs Installer)**, free on the Play Store or F-Droid.

1. Copy the `.apks` file to your phone
2. Open **SAI**
3. Tap **Install APKs**
4. Pick your file
5. Tap **Install** ✅

<br>

## 🗂️ Bonus: download several versions at once

Want multiple versions of the same app? You can do that too.

**Step 1 —** Make a plain text file with one version number per line, like this:

```text
1028424
1028425
```

**Step 2 —** Point BunAPK at that file using `-i`.

⚠️ **Two rules so it actually works:**

1. **Type the FULL path to the file** — the complete location *plus* the file name *plus* its `.txt` ending. If you only type the file name, BunAPK won't be able to find the file.
2. **Always wrap the path in "double quotes"** — folders sometimes have spaces in their names, and without quotes the command breaks.

✅ Like this (Android / Termux):

```bash
bunapk com.example.app -i "/storage/emulated/0/Download/my versions.txt"
```

> 💡 Your path looks different on other devices — on Mac/Linux it might be `"/Users/you/Documents/my versions.txt"`, and on Windows `"C:\Users\you\Documents\my versions.txt"`. The two rules (full path + double quotes) are the same everywhere.

Only want the first few from the list? Add `-l` and a number:

```bash
bunapk com.example.app -i "/storage/emulated/0/Download/my versions.txt" -l 3
```

<br>

## 🤓 Under the hood (for the technically curious)

If you want to know *exactly* what BunAPK pulls down, here are the details.

### 🧩 What actually gets downloaded

A modern Play Store app isn't a single file — it's an **Android App Bundle** split into many smaller APKs. BunAPK collects all of them and zips them into one installable `.apks` file (the base APK plus every `split_config.*.apk`). If an app has no splits, you simply get one standalone `.apk`.

To make Google hand over *every* split, BunAPK presents itself as a series of synthetic devices — one for each architecture + density combination — rotating through **23 built-in device profiles**. Every session is authenticated up front in a single "pre-flight" pass, so no split is ever skipped because a token dropped mid-run.

### 🛠️ CPU architectures (ABIs) — 2

| ABI | What it's for |
| :--- | :--- |
| `arm64-v8a` | 64-bit ARM — virtually every modern phone |
| `armeabi-v7a` | 32-bit ARM — older and low-end devices |

### 📐 Screen densities — 7 (ldpi → xxxhdpi)

| DPI | Bucket |
| :--- | :--- |
| `120` | ldpi |
| `160` | mdpi |
| `213` | tvdpi |
| `240` | hdpi |
| `320` | xhdpi |
| `480` | xxhdpi |
| `640` | xxxhdpi |

### 🌐 Languages — 24

`ar` Arabic · `de` German · `en` English · `es` Spanish · `et` Estonian · `fi` Finnish · `fr` French · `hi` Hindi · `hu` Hungarian · `in` Indonesian · `it` Italian · `ja` Japanese · `ko` Korean · `ms` Malay · `nl` Dutch · `pl` Polish · `pt` Portuguese · `ru` Russian · `sv` Swedish · `th` Thai · `tr` Turkish · `uk` Ukrainian · `vi` Vietnamese · `zh` Chinese

### ⚙️ How the splits are gathered efficiently

Rather than brute-forcing every possible combination, BunAPK queries **all densities on `arm64-v8a`** (the most compatible architecture) to harvest the density and language splits, then queries each remaining architecture once at a standard density to grab its architecture-specific splits. The result is full coverage with far fewer requests.

### 🔐 Authentication

BunAPK signs in **anonymously** through a public token dispenser — no Google account and no personal data. That token is what lets it talk to Google Play's download API on your behalf.

<br>

## ⚠️ Please use this responsibly

Only download apps you're actually allowed to have, and follow the Google Play terms of service. Be cool. 🙏

<br>

## 🙏 Credits & acknowledgements

BunAPK is based on **[gplaydl by rehmatworks](https://github.com/rehmatworks/gplaydl)** — big thanks for the original idea and groundwork that made this possible.

BunAPK takes that foundation and pushes it further: **complete bundles** (every architecture, density, and language), `.apks` packaging, old-version downloads, and a simpler one-command experience.

<br>

## 👤 Author

Made by **[UltraMotionOfficial](https://github.com/UltraMotionOfficial)**.
