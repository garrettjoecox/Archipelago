# 2 Ship 2 Harkinian (MM) Setup Guide

## Required Software

- [2 Ship 2 Harkinian](https://www.2ship2harkinian.com/) — Windows, Linux (including Steam Deck) and Mac are supported.
- A The Legend of Zelda: Majora's Mask ROM (US version).
- Until Archipelago support is integrated into the main 2S2H builds, a build that includes it (see the releases on the
  Archipelago-2S2H page).
- If hosting or generating yourself, the `mm_2ship.apworld` from the same releases page.

Important: the apworld and the game build are released together and must come from the same release — location IDs are
shared between them.

## Installation

### Installing 2 Ship 2 Harkinian

Follow the instructions in the README that comes with your 2S2H download to get the game set up, including extracting
the ROM assets from your Majora's Mask copy.

### How to play Archipelago on 2 Ship 2 Harkinian

In 2 Ship 2 Harkinian's quest select menu, select Archipelago and follow the on-screen instructions to enter your
server address, slot name and password. After creating the save file, it is linked to your Archipelago slot and will
automatically try to connect whenever it is loaded.

In the ESC menu you can find the built-in Archipelago console under the "Network" tab. The built-in check tracker in
the Randomizer section works in Archipelago saves, as do the usual 2S2H enhancements and quality-of-life options.

## Configure Archipelago Options

### Configure Your YAML File

In the Archipelago Launcher, choose "Install APWorld" and pick the `mm_2ship.apworld` file that came with your
download. Then choose "Generate Template Options", which writes template yamls into your Archipelago installation
under `Players/Templates`. Edit `2 Ship 2 Harkinian (MM).yaml` with your text editor of choice — every option carries
a description explaining what it does.
