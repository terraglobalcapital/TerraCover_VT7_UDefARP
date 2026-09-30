# Verra UDef-ARP reference code

The comparison documents in [`docs/`](docs) measure this package against Verra's own
UDef-ARP releases. Those releases are **not** part of this repository: they are third-party
code with their own provenance and licence, obtained from Verra / Clark Labs, and
`.gitignore` keeps them out even when they sit in a `verra_code/` folder beside this
package for the comparison work.

A comparison is only checkable if both sides are pinned, so this file records exactly which
bytes were compared against. To verify a copy, hash it and match it here.

```bash
# one release, from the repository root
find verra_code/UDef-ARP-2.14.1 -type f -print0 | sort -z \
  | xargs -0 sha256sum
```

## Releases

| Release | Files | Bytes |
|---|---:|---:|
| `(root)` | 1 | 36 |
| `UDef-ARP-2.14.1` | 46 | 7,949,331 |
| `UDef-ARP-main` | 46 | 5,008,125 |
| `UDef-ARP-main 2.11` | 47 | 7,948,786 |
| **total** | **140** | **20,906,278** |

`UDef-ARP-main` is the original public release, `UDef-ARP-main 2.11` and
`UDef-ARP-2.14.1` the later ones. 2.14.1 differs from 2.11 in `model_evaluation.py` alone.

## SHA-256 manifest

### `(root)`

| File | SHA-256 | Bytes |
|---|---|---:|
| `ReadMe.txt` | `2b7c82cc461ff5802a6588d6825370c35af06c96515e70da0934768d8822eafc` | 36 |

### `UDef-ARP-2.14.1`

| File | SHA-256 | Bytes |
|---|---|---:|
| `LICENSE` | `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986` | 35,149 |
| `README.md` | `852bb4b79f6ea402aed7c2156e981bed655d0f9024e318488c0ae48483676248` | 4,803 |
| `UDef-ARP.py` | `f4c6310d2b14b441c520f05b47c99cc1aea9042ac8f3c5b6bb5e83c27ca46c7d` | 148,652 |
| `UDef-ARP_conda_env.yml` | `9b06427fec2854c2f363b256ca5f4de9ed6d3fce000df455463254aedc8e357e` | 8,127 |
| `allocation_tool.py` | `3007c1988b7dedd44f34d51fbf93eed9712c595baf6372364ba2994df4317254` | 25,986 |
| `data/Verra.png` | `a137766215680c39c7569e791deeaf5a0092a9474c8a7465b500978e51ac3674` | 6,223 |
| `data/at_fit_cal_screen.ui` | `c329d64249ea8eadf78e39561f4bc286ccd19cb5b7948077d3301c79a8719c60` | 19,901 |
| `data/at_fit_hrp_screen.ui` | `274a0c50e4c33a24f4a44ee26b4f46925f8e8223b6572ba5cb24ca3abab09035` | 17,547 |
| `data/at_pre_cnf_screen.ui` | `ccaeeab6dd0dd504b76f80561c68d5c803cb6e708559a3e14585f1e11e49d236` | 20,061 |
| `data/at_pre_vp_screen.ui` | `c1c8b16327be67b1c685a8c071e4ca66975a52458f20c79e1e42f84ac7be49f9` | 20,842 |
| `data/clark lab logo.png` | `6463f5ecba57016c41169da15105941719ca257cb58f4ff31459f7318138decb` | 36,576 |
| `data/icon.ico` | `d2148bb2e90d3f5bb4193e9738eb339dc17632344116319be49bed8fcd634638` | 165,662 |
| `data/icon_logo.jpg` | `82f223d4a29e513d8653fd493171fc47dc37b8da97db152decb393731a27cadc` | 4,140 |
| `data/image_fitcal.jpg` | `4cf429c3bab65cf34f8105a120f1e0beb6fd10c17b6fa3bedb1896b837e5cd43` | 156,445 |
| `data/image_fithrp.jpg` | `26018137888f48b35471aeeb5d052ba833070064e532a45f817af6cad5803dfc` | 157,795 |
| `data/image_intro.jpg` | `ac11c37f25cc88a0f425d5761b610e1ec69a914b74e0c8c66aa4e1d17ac8bef6` | 158,879 |
| `data/image_precnf.jpg` | `4bd54d0e9d5ac15b377bc3a7a64a92f01cc1ac5f4b5372242ba5316bd625acb6` | 157,062 |
| `data/image_prepare.jpg` | `3d14ea919d518f272357209fd2d0fdd264c000568ada34e01b1903c15cb252f0` | 155,589 |
| `data/image_preprocess.jpg` | `2911c8c86a05e3b2f5bd42aee1193554f5a26aa0cb1ee8357703c728cff1adcb` | 155,879 |
| `data/image_prevp.jpg` | `ed1b1e8e2aac9600c8c3a540b640f6464e9ed8f58a061bb16579a64526095c51` | 156,679 |
| `data/intro.jpg` | `9379fe29448a3ba20163dc6645eee767a76d34e24914970fd9ed7e0c494c41b7` | 142,899 |
| `data/intro_screen.png` | `5f65d71339a71a69d6e7466a365e4fc3cbfca7f8b91108842a8301fbba63654a` | 2,154,750 |
| `data/intro_screen.ui` | `9238eaf79c7c122749f104b442b4cd20db4874a1ce732309ba5c269fa1b703b4` | 9,826 |
| `data/mct_fit_cal_screen.ui` | `54de1f14b4937bebe66940418c19bfc341f788f8322926846e819598a436752c` | 20,941 |
| `data/mct_pre_cnf_screen.ui` | `eefba7542c69b9940f3fee68aa6856dc682bee51723dc8b96981852275a2c843` | 25,057 |
| `data/rmt_fit_cal_screen.ui` | `743d95d41314c9d8e31fc3cef45fe306238b93c07b992828dd5d2340d3cc2377` | 35,636 |
| `data/rmt_fit_hrp_screen.ui` | `f71f6b5d658fdd04ce734c394a75a8d5eb5f96e7a6b47ff61513f07f169873f6` | 31,309 |
| `data/rmt_pre_cnf_screen.ui` | `75ebdf5860b452082b3015e770ef9a37dddf9e4712769f4c82edb73b032e8e9f` | 32,191 |
| `data/rmt_pre_vp_screen.ui` | `dd002382d435dd59124e7973a711d4d05e694ac859569f8c96c6e7a38a61e00d` | 33,468 |
| `data/stage.PNG` | `0bcf81a54c7458f271b2c3ad257c3cda6b4c651eecd85e8c9c06654947342038` | 73,381 |
| `data/terra carbon logo.png` | `73ac6056d49ede83012a57e662ba8c91df4f98f425e7a1f0424b14ab5fe7000f` | 5,210 |
| `data/vcs.png` | `14b54b2cc98a8c5caa6517d94312bc701dd1ef83fef24439206ed9bf7329d4d9` | 9,168 |
| `doc/AppFitAM.pdf` | `ced2b90c35a446b6d2ce57b88c499aa8d33958bc86ad3b5dc4756f82a2d58e03` | 229,425 |
| `doc/AppFitVM.pdf` | `e9ea071e4e3a9ff92a1cb8a6d6d938e69b03d74bf7225c296d69d0aefddc0514` | 427,761 |
| `doc/AppPreAM.pdf` | `7e1ea8ffdd7c55e44be45aacc38285bd01d01b478f42c590499e93f877099d68` | 235,337 |
| `doc/AppPreVM.pdf` | `db8704a5c0adda5f0cf49728c8653ea644410d1220be4a8893a5bc4b6f16a658` | 407,582 |
| `doc/TestFitAM.pdf` | `15924466dc813ddde72fd943d59a2effb9ef843635b8ed1927dddd8db49377a8` | 228,844 |
| `doc/TestFitMA.pdf` | `84288eab1b47d555365f8587e4f554df497eb26ad247dd888a66564f76b7fc00` | 231,165 |
| `doc/TestFitVM.pdf` | `4b61814053d084eaa3bdb03dcfa75ae7dcf16c6dbeb4b92f96a4879c48c55b85` | 411,813 |
| `doc/TestPreAM.pdf` | `1f89bef0cf2e808c3776ab692e8e67f50135231a575d40aef09419eea3593734` | 233,100 |
| `doc/TestPreMA.pdf` | `7fa0319a5d6e7d93ed7b8f7cbb50dc91c8f4fe9db2a8923725671b36fd4a2eb7` | 413,526 |
| `doc/TestPreVM.pdf` | `3afae629186468340c34005154822e3ae55e9d30e60cde1bc5301896d0aaecd7` | 407,214 |
| `doc/UDef-ARP_Introduction.pdf` | `15874276b225a76d2ea23cc5b70f8a365c971c35a155f86193e6688f07b11749` | 426,495 |
| `font/AvenirNextLTPro-DemiCn.otf` | `cde55e31aefe9d6f6fa7293d9c28f463d6d486944ee5abdcba4046384e3daf39` | 70,064 |
| `model_evaluation.py` | `d4694393f66853017b4a372fbcad872dcb36b0b7d233ee3f5b44be9d30a5eec3` | 29,594 |
| `vulnerability_map.py` | `18712914d3378348f95ee89992d3b502d2014ebb87d0b442231a9753f8bf7442` | 11,578 |

### `UDef-ARP-main`

| File | SHA-256 | Bytes |
|---|---|---:|
| `LICENSE` | `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986` | 35,149 |
| `README.md` | `6ed6a46842e65343259ac5fb394a9a0c3e9850e5c2d9f0c19dd433ed135cf9a8` | 4,348 |
| `UDef-ARP.py` | `c3cfa7a228fa59399b704ca207d0be22c4f2bde436ffc93840270b102e2c70f6` | 111,220 |
| `UDef-ARP_conda_env.yml` | `81d94901e90a33c0e596039f1d7dbe4376b73238102b8ca45bca2eeb2d535895` | 8,091 |
| `allocation_tool.py` | `d064f861d8761a5c3db8e2ba50473c044124fb09839c7aeccbf424a8ca2316b6` | 25,694 |
| `data/Thumbs.db` | `15e8f3b9f9748ab29d5c2593ac70618ed135f5b578fa1672e0c1c1a8157440e4` | 4,096 |
| `data/Verra.png` | `a137766215680c39c7569e791deeaf5a0092a9474c8a7465b500978e51ac3674` | 6,223 |
| `data/at_fit_cal_screen.ui` | `0c448b8f0969a1532829cee8c03e11f2d77d5bf7f33380238399f637f8ccaa72` | 19,961 |
| `data/at_fit_hrp_screen.ui` | `8f89cd25ce03a5452660f4fbaeec87de2608a7f5c3922e11457327a19beaaba9` | 17,607 |
| `data/at_pre_cnf_screen.ui` | `050c9fdf1b84d6606ea7e8128b99b971e6937e76d6958306e438bf91afb858c4` | 20,104 |
| `data/at_pre_vp_screen.ui` | `2ae15db45025ce5001b7fc5a49b16729483b7b5279aec77aa28a099e6002fadd` | 22,188 |
| `data/clark lab logo.png` | `6463f5ecba57016c41169da15105941719ca257cb58f4ff31459f7318138decb` | 36,576 |
| `data/icon.ico` | `d2148bb2e90d3f5bb4193e9738eb339dc17632344116319be49bed8fcd634638` | 165,662 |
| `data/icon_logo.jpg` | `82f223d4a29e513d8653fd493171fc47dc37b8da97db152decb393731a27cadc` | 4,140 |
| `data/image_fitcal.jpg` | `4cf429c3bab65cf34f8105a120f1e0beb6fd10c17b6fa3bedb1896b837e5cd43` | 156,445 |
| `data/image_fithrp.jpg` | `26018137888f48b35471aeeb5d052ba833070064e532a45f817af6cad5803dfc` | 157,795 |
| `data/image_intro.jpg` | `ac11c37f25cc88a0f425d5761b610e1ec69a914b74e0c8c66aa4e1d17ac8bef6` | 158,879 |
| `data/image_precnf.jpg` | `4bd54d0e9d5ac15b377bc3a7a64a92f01cc1ac5f4b5372242ba5316bd625acb6` | 157,062 |
| `data/image_prepare.jpg` | `3d14ea919d518f272357209fd2d0fdd264c000568ada34e01b1903c15cb252f0` | 155,589 |
| `data/image_preprocess.jpg` | `2911c8c86a05e3b2f5bd42aee1193554f5a26aa0cb1ee8357703c728cff1adcb` | 155,879 |
| `data/image_prevp.jpg` | `ed1b1e8e2aac9600c8c3a540b640f6464e9ed8f58a061bb16579a64526095c51` | 156,679 |
| `data/intro.jpg` | `9379fe29448a3ba20163dc6645eee767a76d34e24914970fd9ed7e0c494c41b7` | 142,899 |
| `data/intro_screen.png` | `5f65d71339a71a69d6e7466a365e4fc3cbfca7f8b91108842a8301fbba63654a` | 2,154,750 |
| `data/intro_screen.ui` | `9238eaf79c7c122749f104b442b4cd20db4874a1ce732309ba5c269fa1b703b4` | 9,826 |
| `data/mct_fit_cal_screen.ui` | `739b1876e294ef85e26b30663c4c116f335efe291f577a5f0542f408b509ebc3` | 20,962 |
| `data/mct_pre_cnf_screen.ui` | `44fcd2d03310510b7f31735be3ead32203d669ae2c3714680e66242e203199e8` | 25,144 |
| `data/rmt_fit_cal_screen.ui` | `33e00562a4ff5ec90649f3db6f062929926149a9bdc977b9826678e369c9f055` | 35,723 |
| `data/rmt_fit_hrp_screen.ui` | `8184a71e1f5e2172cb6f1d95b394c6b0a75a745627262099ac620f7f61ae3309` | 29,831 |
| `data/rmt_pre_cnf_screen.ui` | `fdfdc947a2ea34c033dd03bbe9f5cef6f690090bd2ec86f667e91adea25fcc47` | 30,521 |
| `data/rmt_pre_vp_screen.ui` | `f725eba29e8277b492ef1e2e3ddf17e837863bce248ffad03fd023648e5c8b7a` | 32,096 |
| `data/terra carbon logo.png` | `73ac6056d49ede83012a57e662ba8c91df4f98f425e7a1f0424b14ab5fe7000f` | 5,210 |
| `data/vcs.png` | `14b54b2cc98a8c5caa6517d94312bc701dd1ef83fef24439206ed9bf7329d4d9` | 9,168 |
| `doc/AppFitAM.pdf` | `7b26fe62f400cb2619556089bc9a820cf235b216b23f2c7a565640fb3862e277` | 53,465 |
| `doc/AppFitVM.pdf` | `2246e35b4ba881f8652c718a2b65cbc88834c36dcb44b8dbf3a36fa893feeba7` | 86,411 |
| `doc/AppPreAM.pdf` | `5f3a86a4aae47497c02951dbab208cd532b9e546cbf403c0fdeae9e8341f5a4d` | 56,051 |
| `doc/AppPreVM.pdf` | `7ffdf115f1e4ef8d4a5ff1d6b5be20c7f96756c012a337b8df10b26f9a042375` | 80,208 |
| `doc/TestFitAM.pdf` | `0f11bf411515abb4e19ccf45f15ae7f9e32bf02e9491a85a3056e75268b1d561` | 53,238 |
| `doc/TestFitMA.pdf` | `fce48c9da2934a26c390d2b501f94f1872491a9ff8e8ac1892bb925d8d55855d` | 70,807 |
| `doc/TestFitVM.pdf` | `d9d5c76fe1e0af8d402d9a43cca26708a94a9beb0e67f6dbc0175b034df214b8` | 82,533 |
| `doc/TestPreAM.pdf` | `bbac7f399181790bd82ce4659147c7038cfbf2a86342fcb2dfe97a9cdf68284c` | 76,561 |
| `doc/TestPreMA.pdf` | `b4902da050437fc503f5236cd0b0cc59d922f63a9c4df039a7b480f17f5eb0cd` | 71,356 |
| `doc/TestPreVM.pdf` | `5be1464e848b35e80ae109599e21583e6830105add0c245eb7181d5cc1966c09` | 79,862 |
| `doc/UDef-ARP_Introduction.pdf` | `40e13442be0d9923579f7e210bb210f51e6673fe91256f1c8cef25c57b6472d8` | 112,157 |
| `font/AvenirNextLTPro-DemiCn.otf` | `cde55e31aefe9d6f6fa7293d9c28f463d6d486944ee5abdcba4046384e3daf39` | 70,064 |
| `model_evaluation.py` | `9276e96247742dfdcbb7ea11624d3111527ee456422f6ed4d5c0f405ada51cd4` | 24,337 |
| `vulnerability_map.py` | `12b8189b3a140d24da72d58e6acf9203f9ce6d45ea08e920c0265854067b2746` | 15,558 |

### `UDef-ARP-main 2.11`

| File | SHA-256 | Bytes |
|---|---|---:|
| `LICENSE` | `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986` | 35,149 |
| `README.md` | `852bb4b79f6ea402aed7c2156e981bed655d0f9024e318488c0ae48483676248` | 4,803 |
| `UDef-ARP.py` | `f4c6310d2b14b441c520f05b47c99cc1aea9042ac8f3c5b6bb5e83c27ca46c7d` | 148,652 |
| `UDef-ARP_conda_env.yml` | `81d94901e90a33c0e596039f1d7dbe4376b73238102b8ca45bca2eeb2d535895` | 8,091 |
| `allocation_tool.py` | `3007c1988b7dedd44f34d51fbf93eed9712c595baf6372364ba2994df4317254` | 25,986 |
| `data/Thumbs.db` | `0129de99cbd9086b00f7e5ffb389b032ef17c4771f02002b8f0080424e970b03` | 4,096 |
| `data/Verra.png` | `a137766215680c39c7569e791deeaf5a0092a9474c8a7465b500978e51ac3674` | 6,223 |
| `data/at_fit_cal_screen.ui` | `c329d64249ea8eadf78e39561f4bc286ccd19cb5b7948077d3301c79a8719c60` | 19,901 |
| `data/at_fit_hrp_screen.ui` | `274a0c50e4c33a24f4a44ee26b4f46925f8e8223b6572ba5cb24ca3abab09035` | 17,547 |
| `data/at_pre_cnf_screen.ui` | `ccaeeab6dd0dd504b76f80561c68d5c803cb6e708559a3e14585f1e11e49d236` | 20,061 |
| `data/at_pre_vp_screen.ui` | `c1c8b16327be67b1c685a8c071e4ca66975a52458f20c79e1e42f84ac7be49f9` | 20,842 |
| `data/clark lab logo.png` | `6463f5ecba57016c41169da15105941719ca257cb58f4ff31459f7318138decb` | 36,576 |
| `data/icon.ico` | `d2148bb2e90d3f5bb4193e9738eb339dc17632344116319be49bed8fcd634638` | 165,662 |
| `data/icon_logo.jpg` | `82f223d4a29e513d8653fd493171fc47dc37b8da97db152decb393731a27cadc` | 4,140 |
| `data/image_fitcal.jpg` | `4cf429c3bab65cf34f8105a120f1e0beb6fd10c17b6fa3bedb1896b837e5cd43` | 156,445 |
| `data/image_fithrp.jpg` | `26018137888f48b35471aeeb5d052ba833070064e532a45f817af6cad5803dfc` | 157,795 |
| `data/image_intro.jpg` | `ac11c37f25cc88a0f425d5761b610e1ec69a914b74e0c8c66aa4e1d17ac8bef6` | 158,879 |
| `data/image_precnf.jpg` | `4bd54d0e9d5ac15b377bc3a7a64a92f01cc1ac5f4b5372242ba5316bd625acb6` | 157,062 |
| `data/image_prepare.jpg` | `3d14ea919d518f272357209fd2d0fdd264c000568ada34e01b1903c15cb252f0` | 155,589 |
| `data/image_preprocess.jpg` | `2911c8c86a05e3b2f5bd42aee1193554f5a26aa0cb1ee8357703c728cff1adcb` | 155,879 |
| `data/image_prevp.jpg` | `ed1b1e8e2aac9600c8c3a540b640f6464e9ed8f58a061bb16579a64526095c51` | 156,679 |
| `data/intro.jpg` | `9379fe29448a3ba20163dc6645eee767a76d34e24914970fd9ed7e0c494c41b7` | 142,899 |
| `data/intro_screen.png` | `5f65d71339a71a69d6e7466a365e4fc3cbfca7f8b91108842a8301fbba63654a` | 2,154,750 |
| `data/intro_screen.ui` | `9238eaf79c7c122749f104b442b4cd20db4874a1ce732309ba5c269fa1b703b4` | 9,826 |
| `data/mct_fit_cal_screen.ui` | `54de1f14b4937bebe66940418c19bfc341f788f8322926846e819598a436752c` | 20,941 |
| `data/mct_pre_cnf_screen.ui` | `eefba7542c69b9940f3fee68aa6856dc682bee51723dc8b96981852275a2c843` | 25,057 |
| `data/rmt_fit_cal_screen.ui` | `743d95d41314c9d8e31fc3cef45fe306238b93c07b992828dd5d2340d3cc2377` | 35,636 |
| `data/rmt_fit_hrp_screen.ui` | `f71f6b5d658fdd04ce734c394a75a8d5eb5f96e7a6b47ff61513f07f169873f6` | 31,309 |
| `data/rmt_pre_cnf_screen.ui` | `75ebdf5860b452082b3015e770ef9a37dddf9e4712769f4c82edb73b032e8e9f` | 32,191 |
| `data/rmt_pre_vp_screen.ui` | `dd002382d435dd59124e7973a711d4d05e694ac859569f8c96c6e7a38a61e00d` | 33,468 |
| `data/stage.PNG` | `0bcf81a54c7458f271b2c3ad257c3cda6b4c651eecd85e8c9c06654947342038` | 73,381 |
| `data/terra carbon logo.png` | `73ac6056d49ede83012a57e662ba8c91df4f98f425e7a1f0424b14ab5fe7000f` | 5,210 |
| `data/vcs.png` | `14b54b2cc98a8c5caa6517d94312bc701dd1ef83fef24439206ed9bf7329d4d9` | 9,168 |
| `doc/AppFitAM.pdf` | `ced2b90c35a446b6d2ce57b88c499aa8d33958bc86ad3b5dc4756f82a2d58e03` | 229,425 |
| `doc/AppFitVM.pdf` | `e9ea071e4e3a9ff92a1cb8a6d6d938e69b03d74bf7225c296d69d0aefddc0514` | 427,761 |
| `doc/AppPreAM.pdf` | `7e1ea8ffdd7c55e44be45aacc38285bd01d01b478f42c590499e93f877099d68` | 235,337 |
| `doc/AppPreVM.pdf` | `db8704a5c0adda5f0cf49728c8653ea644410d1220be4a8893a5bc4b6f16a658` | 407,582 |
| `doc/TestFitAM.pdf` | `15924466dc813ddde72fd943d59a2effb9ef843635b8ed1927dddd8db49377a8` | 228,844 |
| `doc/TestFitMA.pdf` | `84288eab1b47d555365f8587e4f554df497eb26ad247dd888a66564f76b7fc00` | 231,165 |
| `doc/TestFitVM.pdf` | `4b61814053d084eaa3bdb03dcfa75ae7dcf16c6dbeb4b92f96a4879c48c55b85` | 411,813 |
| `doc/TestPreAM.pdf` | `1f89bef0cf2e808c3776ab692e8e67f50135231a575d40aef09419eea3593734` | 233,100 |
| `doc/TestPreMA.pdf` | `7fa0319a5d6e7d93ed7b8f7cbb50dc91c8f4fe9db2a8923725671b36fd4a2eb7` | 413,526 |
| `doc/TestPreVM.pdf` | `3afae629186468340c34005154822e3ae55e9d30e60cde1bc5301896d0aaecd7` | 407,214 |
| `doc/UDef-ARP_Introduction.pdf` | `15874276b225a76d2ea23cc5b70f8a365c971c35a155f86193e6688f07b11749` | 426,495 |
| `font/AvenirNextLTPro-DemiCn.otf` | `cde55e31aefe9d6f6fa7293d9c28f463d6d486944ee5abdcba4046384e3daf39` | 70,064 |
| `model_evaluation.py` | `55df6b4d780504490ce5e80e4a7e55b4b15cdde2880c3f5d225a8a8122f32afb` | 24,989 |
| `vulnerability_map.py` | `18712914d3378348f95ee89992d3b502d2014ebb87d0b442231a9753f8bf7442` | 11,578 |

