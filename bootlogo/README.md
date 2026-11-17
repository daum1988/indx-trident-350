# Boot logo (Plymouth) for Raspberry Pi CM4 / MainsailOS

Shows a centred logo on the attached display instead of the Linux boot text.

1. Put your own square-ish `logo.png` into this folder (no logo is shipped,
   use one you have the rights to).
2. Copy the folder to the Pi, e.g. `~/printer_data/config/bootlogo/`.
3. `bash ~/printer_data/config/bootlogo/install.sh`, then `sudo reboot`.

The script backs up `cmdline.txt` / `config.txt` once (`*.vor_bootlogo`) and can
be run again safely.

**Logo appears rotated?** The framebuffer is not rotated during boot (display
rotation from KlipperScreen/X applies later). Plymouth's own rotate function
clips non-square images, so rotate the PNG itself in the opposite direction
and run `install.sh` again.

---

**Deutsch:** Eigenes `logo.png` in diesen Ordner legen, Ordner auf den Pi
kopieren, `install.sh` ausführen, neu starten. Steht das Logo um 90° gedreht,
das PNG selbst in die Gegenrichtung drehen und `install.sh` erneut ausführen.
