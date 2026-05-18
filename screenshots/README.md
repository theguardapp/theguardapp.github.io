# Screenshots folder

These are the in-app screenshots rendered inside the phone frames on the
landing page (`index.html`, section `#spotlight`).

The spotlight section has six alternating rows. Three are solo (one phone per
row) and three are dual (two overlapping phones via `.spotlight-img--pair` —
the "back" phone is rotated -7° behind the "front" phone at +5°).

| Row | Layout | Front phone                                | Back phone                                       |
|-----|--------|--------------------------------------------|--------------------------------------------------|
| 1   | DUAL   | `Dashboard_The Guard.jpg`                  | `Memory_page_The Guard.jpg`                      |
| 2   | SOLO   | `Storage_page_The Guard.jpg`               | —                                                |
| 3   | DUAL   | `Battery_page_The Guard.jpg`               | `Live_charging_analysis_The Guard.jpg`           |
| 4   | DUAL   | `Thermals_The Guard.jpg`                   | `Power_draw_analytics_The Guard.jpg`             |
| 5   | SOLO   | `Recovery_The Guard.jpg`                   | —                                                |
| 6   | DUAL   | `Privacy_policy_The Guard.jpg`             | `A_glimpse_of_deep_app_analysis_The Guard.jpg`   |

File names contain spaces; `index.html` URL-encodes them as `%20`.

Recommended capture size: **1080×2340** (or any 9:19.5 ratio) so each image
fills the phone frame without cropping. JPG is fine for in-device captures;
PNG is preferred for any composite with transparency.
