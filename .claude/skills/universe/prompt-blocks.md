# 유니버스 캐릭터 프롬프트 블록 (영상·이미지 모델용)

영상/이미지 프롬프트에 캐릭터가 나오면 아래 블록을 **그대로** 붙인다. 문구를 줄이거나 바꾸면 컷마다 얼굴·의상이 달라진다.
가능하면 `sheets/`의 캐릭터 시트를 레퍼런스 이미지로 함께 넣는다 (Seedance 멀티 레퍼런스, Kling Element/Omni-Ref, Higgsfield 레퍼런스 등).

- `[ID]` 블록 = 얼굴·의상 고정 묘사 (모든 컷에 필수)
- `[LOCK]` = 어떤 연출에서도 바뀌면 안 되는 것 (네거티브 체크용)
- `[FX]` = 능력 연출 기본값 (연출 제안 기반이므로 사용자가 바꾸면 따라간다)

---

## 01 무명 (Mumyeong)
Reference: `sheets/01_mumyeong.png`

[ID] a pale young East Asian man who looks in his early twenties but has lived for 500 years, long messy wet-looking dark brown-black hair falling over his face, eyes always closed (blind), a diagonal stitched scar slashing across the bridge of his nose onto both cheeks, wearing an all-white suit: long white tailcoat with sharp asymmetric pointed hems, white double-breasted waistcoat, white shirt, white silk tie, white trousers, white ankle boots with silver metal heel caps, silver rings, a white katana in a white scabbard worn on his left hip, white-wrapped hilt, silver hexagonal mechanical tsuba, silver bands on the scabbard, two white cords hanging from it

[LOCK] eyes never open · scar across nose bridge · everything white and silver · sword on left hip

[FX] near-motionless stance, then a single instantaneous draw (iaido), a thin silent white-silver flash line, delayed cut, dust and hair lifting after the slash

---

## 02 서현 아빠 / 좀비 아빠 (Zombie Dad)
Reference: `sheets/02_zombie-dad.png`

[ID] an East Asian man in his forties turned zombie but still human at heart, shaggy messy black hair streaked with grey, unkempt grey-streaked beard, milky white pupil-less eyes, dried blood streaks running from his right eye, dirt-smeared greyish skin, wearing a beige short-sleeve T-shirt riddled with holes and frayed hems and stained with blood, dark distressed black jeans torn at the knees with shredded hems, dirty white sneakers, a worn dark leather crossbody sling bag across his chest — modern clothes, out of place in a martial arts world

[LOCK] milky white eyes · ragged modern clothes (never wuxia robes) · crossbody bag

[FX] karate stance and straight punches (seiken) with monstrous zombie strength, shockwaves that crack stone and blast walls, heavy grounded impacts

---

## 03 서현 (Seohyun)
Reference: `sheets/03_seohyun.png`

[ID] a young East Asian woman in her early twenties, the Fist God and Martial Alliance Leader, long straight dark brown hair with a center part and see-through bangs, brown eyes, light freckles, a stitched scar on her right cheek running from below the eye toward the jaw, calm resolute expression, wearing a black silk wuxia hanfu robe with gold cloud and floral embroidery and structured shoulders over an ivory cross-collar inner robe, wide sleeves with ivory inner sleeves and black-gold embroidered cuffs, black embroidered waist sash with a metal ornament and a long hanging front panel, full pleated floor-length skirt, black boots

[LOCK] scar on right cheek · black-gold-ivory robe · see-through bangs

[FX] wuxia fist techniques mixed with karate fundamentals, golden fist-force (quan jin) bursts, wide sleeves billowing with each strike

---

## 04 시율 (Siyul)
Reference: `sheets/04_siyul.png`

[ID] a Korean woman in her twenties, former taekwondo athlete, silver-white hair in a high side ponytail with face-framing strands, grey eyes, sharp winged eyeliner, large gold hoop chain earrings, chunky silver chain necklace, cropped white and sky-blue windbreaker track jacket with a high collar, open front zipper, elastic cuffs and a Korean flag (Taegukgi) patch on the left chest, sky-blue sports crop top with two white stripes, toned abs, white wide-leg track pants with sky-blue side stripes, a cargo pocket and a black strap harness with D-rings and Korean lettering, chunky white sneakers

[LOCK] silver-white side ponytail · white + sky-blue track set · Taegukgi patch on left chest

[FX] flashy taekwondo kicks (spinning back kick, 540 kick, aerial combo kicks), sky-blue and white ki trails bursting from her feet, taegeuk swirl motifs

---

## 05 메이드 / 유모 (The Maid)
Reference: `sheets/05_maid.png`

[ID] a pale woman from another world, long straight black hair with a center part, sharp dark eyebrows, grey eyes, dark smoky eye makeup, cold glaring expression, small black earrings, white ruffled maid headdress with black ribbons, gothic black maid dress with a high frilled collar and a large black ribbon bow at the neck, white puffed blouse front with black buttons, black lace corset with lacing, layered white lace apron with a front pocket, long black sleeves with white cuffs and black bows, short black skirt over layered white lace petticoats with long trailing lace panels, a huge black bow at the back of the waist, white thigh-high stockings with lace garter bands and black bows, black patent ankle-strap high heels with bows

[LOCK] gothic black-and-white maid outfit · black hair center part · cold expression · apron front pocket

[FX] she reaches into her apron front pocket or into thin air, the space ripples like water, and an impossibly large object slides out smoothly (weapons, tea sets, umbrellas, anything) — or forms out of light particles in her hand

---

## 06 홍길동 (Hong Gildong)
Reference: `sheets/06_hong-gildong.png`

[ID] a handsome young East Asian man, Joseon-era righteous outlaw, messy black hair with silver-grey streaks, brown eyes, playful confident smirk, wide weathered woven bamboo-straw hat, indigo-blue robe with white wave patterns over layered ivory inner robes, torn and frayed layered hems, rust-red cloth sashes and scarf fluttering in the wind, multiple brown leather belts with metal rings, brown tassels and a gourd, leather-wrapped forearm guards, dark baggy trousers, leather lace-wrapped boots, a long wooden staff with metal bands and red cloth ties, warm golden backlight with dust in the air

[LOCK] straw hat · indigo robe with wave pattern · rust-red fluttering cloth · wooden staff

[FX] playful Taoist sorcery — shadow clones, shrinking-the-earth teleport steps, shapeshifting, summoning wind and clouds — plus fluid staff and unarmed martial arts, toying with opponents, effortless overwhelming power

---

## 공통 스타일 기본값 (사용자가 다르게 정하면 그쪽을 따름)

- 실사 시네마틱 (캐릭터 시트가 실사 톤)
- 캐릭터 시트의 회색 스튜디오 배경은 프롬프트에 넣지 않는다 — 배경은 장면에 맞게 따로 쓴다
- 한 컷에 여러 캐릭터가 나오면 각자의 [ID] 블록을 모두 넣고, 위치(left/right/foreground)로 구분한다
