-- GenOS Socials Data
-- Auto-generated from UIR

local Socials = {}

Socials["accuse"] = {
    min_victim_pos = 0,
    no_arg_char = "Accuse who??",
}

Socials["applaud"] = {
    min_victim_pos = 0,
    no_arg_char = "Clap, clap, clap.",
    no_arg_room = "$n gives a round of applause.",
}

Socials["beg"] = {
    min_victim_pos = 0,
    no_arg_char = "You beg the gods for mercy.  (No way you're gonna get it! :-))",
    no_arg_room = "The gods fall down laughing at $n's request for mercy.",
    found_char = "You desperately try to squeeze a few coins from $M.",
    found_room = "$n begs you for money.  You gratiously let $m peep at your fortune.",
    found_victim = "$n begs $N for a dime or two -- or twenty!",
    not_found = "Your money-lender seems to be out for the moment.",
    self_char = "How? - begging yourself for money doesn't help.",
}

Socials["bleed"] = {
    min_victim_pos = 0,
    no_arg_char = "You bleed profusely, making an awful mess...",
    no_arg_room = "$n bleeds profusely, making an awful mess...",
}

Socials["blush"] = {
    min_victim_pos = 0,
    no_arg_char = "Your cheeks are burning.",
    no_arg_room = "$n blushes.",
}

Socials["bounce"] = {
    min_victim_pos = 0,
    no_arg_char = "BOIINNNNNNGG!",
    no_arg_room = "$n bounces around.",
}

Socials["bow"] = {
    min_victim_pos = 0,
    no_arg_char = "You bow deeply.",
    no_arg_room = "$n bows deeply.",
    found_char = "You bow before $M.",
    found_room = "$n bows before $N.",
    found_victim = "$n bows before you.",
    not_found = "Who's that?",
    self_char = "You kiss your toes.",
    self_room = "$n folds up like a jacknife and kisses $s own toes.",
}

Socials["brb"] = {
    min_victim_pos = 0,
    no_arg_char = "Come back soon!",
    no_arg_room = "$n will be right back!",
}

Socials["burp"] = {
    min_victim_pos = 0,
    no_arg_char = "You burp loudly.",
    no_arg_room = "$n burps loudly.",
}

Socials["cackle"] = {
    min_victim_pos = 0,
    no_arg_char = "You cackle gleefully.",
    no_arg_room = "$n throws back $s head and cackles with insane glee!",
}

Socials["chuckle"] = {
    min_victim_pos = 0,
    no_arg_char = "You chuckle politely.",
    no_arg_room = "$n chuckles politely.",
}

Socials["clap"] = {
    min_victim_pos = 0,
    no_arg_char = "You clap your small hands together.",
    no_arg_room = "$n shows $s approval by clapping $s small hands together.",
}

Socials["comb"] = {
    min_victim_pos = 0,
    no_arg_char = "You comb your hair -- perfect.",
    no_arg_room = "$n combs $s hair, what a dashing specimen!",
    found_char = "You patiently untangle $N's hair -- what a mess!",
    found_room = "$n tries patiently to untangle $N's hair.",
    found_victim = "$n pulls your hair in an attempt to comb it.",
    not_found = "That person is not here.",
    self_char = "You pull your hair, but it will not be combed.",
    self_room = "$n tries to comb $s tangled hair.",
}

Socials["comfort"] = {
    min_victim_pos = 0,
    no_arg_char = "Do you feel uncomfortable?",
}

Socials["cough"] = {
    min_victim_pos = 0,
    no_arg_char = "Yuck, try to cover your mouth next time!",
    no_arg_room = "$n coughs loudly.",
}

Socials["cringe"] = {
    min_victim_pos = 1,
    no_arg_char = "You cringe in terror.",
    no_arg_room = "$n cringes in terror!",
    found_char = "You cringe away from $M.",
    found_room = "$n cringes away from $N in mortal terror.",
    found_victim = "$n cringes away from you.",
    not_found = "I don't see anyone by that name here.. what are you afraid of?",
    self_char = "I beg your pardon?",
}

Socials["cry"] = {
    min_victim_pos = 0,
    no_arg_char = "Waaaaah..",
    no_arg_room = "$n bursts into tears.",
    found_char = "You cry on $S shoulder.",
    found_room = "$n cries on $N's shoulder.",
    found_victim = "$n cries on your shoulder.",
    not_found = "Who's that?",
    self_char = "You cry to yourself.",
    self_room = "$n sobs quietly to $mself.",
}

Socials["cuddle"] = {
    min_victim_pos = 1,
    no_arg_char = "Who do you feel like cuddling today?",
}

Socials["curse"] = {
    min_victim_pos = 0,
    no_arg_char = "You swear loudly for a long time.",
    no_arg_room = "$n swears: #@*\"*&^$$%@*&!!!!!!",
}

Socials["curtsey"] = {
    min_victim_pos = 0,
    no_arg_char = "You curtsey to your audience.",
    no_arg_room = "$n curtseys gracefully.",
}

Socials["dance"] = {
    min_victim_pos = 1,
    no_arg_char = "Feels silly, doesn't it?",
    no_arg_room = "$n tries to dance breakdance but nearly breaks $s neck!",
    found_char = "You lead $M to the dancefloor.",
    found_room = "$n sends $N across the dancefloor.",
    found_victim = "$n sends you across the dancefloor.",
    not_found = "Eh, WHO?",
    self_char = "You skip and dance around by yourself.",
    self_room = "$n skips a light Fandango.",
}

Socials["daydream"] = {
    min_victim_pos = 1,
    no_arg_char = "You dream of better times.",
    no_arg_room = "$n looks absent-minded, $s eyes staring into space.",
}

Socials["drool"] = {
    min_victim_pos = 1,
    no_arg_char = "You start to drool.",
    no_arg_room = "$n starts to drool.",
    found_char = "You drool all over $N.",
    found_room = "$n drools all over $N.",
    found_victim = "$n drools all over you.",
    not_found = "Pardon??",
    self_char = "Sure, go ahead and drool...yuk!",
    self_room = "$n drools on $mself.  What a sight.",
}

Socials["embrace"] = {
    min_victim_pos = 0,
    no_arg_char = "You reach but come away empty.  :(",
    no_arg_room = "$n reaches out for an embrace, but no one is there.",
    found_char = "You embrace $M warmly.",
    found_room = "$n embraces $N warmly.",
    found_victim = "$n embraces you warmly.",
    not_found = "Alas, your embracee is not here.",
    self_char = "You embrace yourself??",
    self_room = "$n wraps his arms around himself for a warm self-embrace.",
}

Socials["fart"] = {
    min_victim_pos = 0,
    no_arg_char = "Where are your manners?",
    no_arg_room = "$n lets off a real rip-roarer!",
}

Socials["flip"] = {
    min_victim_pos = 0,
    no_arg_char = "You flip head over heels.",
    no_arg_room = "$n flips head over heels.",
}

Socials["flirt"] = {
    min_victim_pos = 1,
    no_arg_char = "You flirt outrageously.",
    no_arg_room = "$n flirts outragously.",
    found_char = "You flirt outrageously with $N.",
    found_room = "$n flirts outrageously with $N.",
    found_victim = "$n flirts outrageously with you.",
    not_found = "Sorry, your dearly beloved is not around.",
    self_char = "You flirt with yourself.  Must look stupid.",
    self_room = "$n thinks $e is the most wonderful person in the world.",
}

Socials["fondle"] = {
    min_victim_pos = 0,
    no_arg_char = "Who needs to be fondled?",
}

Socials["french"] = {
    min_victim_pos = 0,
    no_arg_char = "French whom??",
}

Socials["frown"] = {
    min_victim_pos = 0,
    no_arg_char = "What's bothering you?",
    no_arg_room = "$n frowns.",
}

Socials["fume"] = {
    min_victim_pos = 1,
    no_arg_char = "Take it easy now!  Count to ten, very slowly.",
    no_arg_room = "$n grits $s teeth and fumes with rage.",
    found_char = "You stare at $M, fuming.",
    found_room = "$n stares at $N, fuming with rage.",
    found_victim = "$n stares at you, fuming with rage!",
    not_found = "Fume away.. they ain't here.",
    self_char = "That's right - hate yourself!",
    self_room = "$n clenches $s fists and stomps his feet, fuming with anger.",
}

Socials["gasp"] = {
    min_victim_pos = 0,
    no_arg_char = "You gasp in astonishment.",
    no_arg_room = "$n gasps in astonishment.",
}

Socials["giggle"] = {
    min_victim_pos = 0,
    no_arg_char = "You giggle.",
    no_arg_room = "$n giggles.",
}

Socials["glare"] = {
    min_victim_pos = 0,
    no_arg_char = "You glare at nothing in particular.",
    no_arg_room = "$n glares around $m.",
    found_char = "You glare icily at $M.",
    found_room = "$n glares at $N.",
    found_victim = "$n glares icily at you, you feel cold to your bones.",
    not_found = "You try to glare at somebody who is not present.",
    self_char = "You glare icily at your feet, they are suddenly very cold.",
    self_room = "$n glares at $s feet, what is bothering $m?",
}

Socials["greet"] = {
    min_victim_pos = 0,
    no_arg_char = "Greet Who?",
}

Socials["grin"] = {
    min_victim_pos = 0,
    no_arg_char = "You grin evilly.",
    no_arg_room = "$n grins evilly.",
}

Socials["groan"] = {
    min_victim_pos = 0,
    no_arg_char = "You groan loudly.",
    no_arg_room = "$n groans loudly.",
}

Socials["grope"] = {
    min_victim_pos = 0,
    no_arg_char = "Whom do you wish to grope??",
}

Socials["grovel"] = {
    min_victim_pos = 1,
    no_arg_char = "You grovel in the dirt.",
    no_arg_room = "$n grovels in the dirt.",
    found_char = "You grovel before $M",
    found_room = "$n grovels in the dirt before $N.",
    found_victim = "$n grovels in the dirt before you.",
    not_found = "Who?",
    self_char = "That seems a little silly to me..",
}

Socials["growl"] = {
    min_victim_pos = 0,
    no_arg_char = "Grrrrrrrrrr...",
    no_arg_room = "$n growls.",
}

Socials["hiccup"] = {
    min_victim_pos = 0,
    no_arg_char = "*HIC*",
    no_arg_room = "$n hiccups.",
}

Socials["hug"] = {
    min_victim_pos = 1,
    no_arg_char = "Hug who?",
}

Socials["kiss"] = {
    min_victim_pos = 0,
    no_arg_char = "Isn't there someone you want to kiss?",
}

Socials["laugh"] = {
    min_victim_pos = 0,
    no_arg_char = "You fall down laughing.",
    no_arg_room = "$n falls down laughing.",
}

Socials["lick"] = {
    min_victim_pos = 0,
    no_arg_char = "You lick your mouth and smile.",
    no_arg_room = "$n licks $s mouth and smiles.",
    found_char = "You lick $M.",
    found_room = "$n licks $N.",
    found_victim = "$n licks you.",
    not_found = "Lick away, nobody's here with that name.",
    self_char = "You lick yourself.",
    self_room = "$n licks $mself -- YUCK.",
}

Socials["love"] = {
    min_victim_pos = 0,
    no_arg_char = "You love the whole world.",
    no_arg_room = "$n loves everybody in the world.",
    found_char = "You tell your true feelings to $N.",
    found_room = "$n whispers softly to $N.",
    found_victim = "$n whispers to you sweet words of love.",
    not_found = "Alas, your love is not present...",
    self_char = "Well, we already know you love yourself (lucky someone does!)",
    self_room = "$n loves $mself, can you believe it?",
}

Socials["massage"] = {
    min_victim_pos = 0,
    no_arg_char = "Massage what, thin air?",
}

Socials["moan"] = {
    min_victim_pos = 0,
    no_arg_char = "You start to moan.",
    no_arg_room = "$n starts moaning.",
}

Socials["nibble"] = {
    min_victim_pos = 0,
    no_arg_char = "Nibble on who?",
}

Socials["nod"] = {
    min_victim_pos = 1,
    no_arg_char = "You nod solemnly.",
    no_arg_room = "$n nods solemnly.",
}

Socials["nudge"] = {
    min_victim_pos = 0,
    no_arg_char = "Nudge?  Nudge???  The HELL you say!!!!",
}

Socials["nuzzle"] = {
    min_victim_pos = 1,
    no_arg_char = "Nuzzle who??",
}

Socials["pat"] = {
    min_victim_pos = 0,
    no_arg_char = "Pat who??",
}

Socials["peer"] = {
    min_victim_pos = 1,
    no_arg_char = "You peer around you, uncertain that what you see is actually true.",
    no_arg_room = "$n peers around, looking as if $e has trouble seeing everything clearly.",
}

Socials["point"] = {
    min_victim_pos = 1,
    no_arg_char = "You point whereto?",
    no_arg_room = "$n points in all directions, seemingly confused.",
    found_char = "You point at $M -- $E DOES look funny.",
    found_room = "$n muffles a laugh, pointing at $N.",
    found_victim = "$n points at you... how rude!",
    not_found = "You must have a VERY long index-finger...",
    self_char = "You point at yourself.  Insinuating something?",
    self_room = "$n points at $mself, suggesting that the center of matters is $e.",
}

Socials["poke"] = {
    min_victim_pos = 0,
    no_arg_char = "Poke who??",
}

Socials["ponder"] = {
    min_victim_pos = 1,
    no_arg_char = "You ponder over matters as they appear to you at this moment.",
    no_arg_room = "$n sinks deeply into $s own thoughts.",
}

Socials["pout"] = {
    min_victim_pos = 0,
    no_arg_char = "Ah, don't take it so hard.",
    no_arg_room = "$n pouts.",
}

Socials["pray"] = {
    min_victim_pos = 0,
    no_arg_char = "You feel righteous, and maybe a little foolish.",
    no_arg_room = "$n begs and grovels to the powers that be.",
    found_char = "You crawl in the dust before $M.",
    found_room = "$n falls down and grovels in the dirt before $N.",
    found_victim = "$n kisses the dirt at your feet.",
    not_found = "No such person around; your prayers vanish into the endless voids.",
    self_char = "Talk about narcissism...",
    self_room = "$n performs some strange yoga-exercises and mumbles a prayer to $mself.",
}

Socials["puke"] = {
    min_victim_pos = 0,
    no_arg_char = "You puke.",
    no_arg_room = "$n pukes.",
    found_char = "You puke on $M.",
    found_room = "$n pukes on $N.",
    found_victim = "$n pukes on your clothes!",
    not_found = "Once again?",
    self_char = "You puke on yourself.",
    self_room = "$n pukes on $s clothes.",
}

Socials["punch"] = {
    min_victim_pos = 0,
    no_arg_char = "Punch the air?  Sure, go ahead, fine by me...",
    no_arg_room = "$n starts shadow-boxing.",
    found_char = "You punch $M right in the face!  Yuck, the BLOOD!",
    found_room = "$n punches weakly at $N, missing by miles.",
    found_victim = "$n tries a punch at you but misses by a good quarter-mile...",
    not_found = "Punch who?",
    self_char = "You punch yourself in the face resulting in your own nose being bloodied.",
    self_room = "$n punches $mself in the face, looking kind of stupid.",
}

Socials["purr"] = {
    min_victim_pos = 0,
    no_arg_char = "MMMMEEEEEEEEOOOOOOOOOWWWWWWWWWWWW.",
    no_arg_room = "$n purrs contentedly.",
}

Socials["roll"] = {
    min_victim_pos = 1,
    no_arg_char = "You roll your eyes in disgust.",
    no_arg_room = "$n rolls $s eyes in disgust.",
    found_char = "You look at $M and roll your eyes in disgust.",
    found_room = "$n looks at $N in contempt and rolls $s eyes with disgust.",
    found_victim = "$n stares at you and rolls $s eyes in digust.",
    not_found = "Um... who?",
    self_char = "You roll your eyes, disgusted with your own incompetence.",
    self_room = "$n rolls $s eyes, disgusted with $mself.",
}

Socials["ruffle"] = {
    min_victim_pos = 0,
    no_arg_char = "You've got to ruffle SOMEONE.",
}

Socials["scream"] = {
    min_victim_pos = 0,
    no_arg_char = "ARRRRRRRRRRGH!!!!!",
    no_arg_room = "$n screams loudly!",
}

Socials["shake"] = {
    min_victim_pos = 0,
    no_arg_char = "You shake your head.",
    no_arg_room = "$n shakes $s head.",
    found_char = "You shake $S hand.",
    found_room = "$n shakes $N's hand.",
    found_victim = "$n shakes your hand.",
    not_found = "Sorry good buddy, but that person doesn't seem to be here.",
    self_char = "You are shaken by yourself.",
    self_room = "$n shakes and quivers like a bowlful of jelly.",
}

Socials["shiver"] = {
    min_victim_pos = 0,
    no_arg_char = "Brrrrrrrrr.",
    no_arg_room = "$n shivers uncomfortably.",
}

Socials["shrug"] = {
    min_victim_pos = 0,
    no_arg_char = "You shrug.",
    no_arg_room = "$n shrugs helplessly.",
}

Socials["sigh"] = {
    min_victim_pos = 0,
    no_arg_char = "You sigh.",
    no_arg_room = "$n sighs loudly.",
}

Socials["sing"] = {
    min_victim_pos = 0,
    no_arg_char = "You raise your clear (?) voice towards the sky.",
    no_arg_room = "SEEK SHELTER AT ONCE!  $n has begun to sing.",
}

Socials["slap"] = {
    min_victim_pos = 0,
    no_arg_char = "Normally you slap SOMEBODY.",
}

Socials["smile"] = {
    min_victim_pos = 1,
    no_arg_char = "You smile happily.",
    no_arg_room = "$n smiles happily.",
    found_char = "You smile at $M.",
    found_room = "$n beams a smile at $N.",
    found_victim = "$n smiles at you.",
    not_found = "There's no one by that name around.",
    self_char = "You smile at yourself.",
    self_room = "$n smiles at $mself.",
}

Socials["smirk"] = {
    min_victim_pos = 0,
    no_arg_char = "You smirk.",
    no_arg_room = "$n smirks.",
}

Socials["snap"] = {
    min_victim_pos = 0,
    no_arg_char = "PRONTO!  You snap your fingers.",
    no_arg_room = "$n snaps $s fingers.",
}

Socials["snarl"] = {
    min_victim_pos = 0,
    no_arg_char = "You snarl like a viscious animal.",
    no_arg_room = "$n snarls like a cornered, viscious animal.",
    found_char = "You snarl at $M angrily.  Control yourself!",
    found_room = "$n snarls angrily at $N.  $e seems incapable of controlling $mself.",
    found_victim = "$n snarls viciously at you.  $s self-control seems to have gone bananas.",
    not_found = "Eh?  Who?  Not here, my friend.",
    self_char = "You snarl at yourself, obviously suffering from schizophrenia.",
    self_room = "$n snarls at $mself, and suddenly looks very frightened.",
}

Socials["sneeze"] = {
    min_victim_pos = 0,
    no_arg_char = "Gesundheit!",
    no_arg_room = "$n sneezes.",
}

Socials["snicker"] = {
    min_victim_pos = 0,
    no_arg_char = "You snicker softly.",
    no_arg_room = "$n snickers softly.",
}

Socials["sniff"] = {
    min_victim_pos = 0,
    no_arg_char = "You sniff sadly.  *SNIFF*",
    no_arg_room = "$n sniffs sadly.",
}

Socials["snore"] = {
    min_victim_pos = 0,
    no_arg_char = "Zzzzzzzzzzzzzzzzz.",
    no_arg_room = "$n snores loudly.",
}

Socials["snowball"] = {
    min_victim_pos = 0,
    no_arg_char = "Who do you want to throw a snowball at??",
}

Socials["snuggle"] = {
    min_victim_pos = 1,
    no_arg_char = "Who?",
}

Socials["spank"] = {
    min_victim_pos = 0,
    no_arg_char = "You spank WHO?  Eh?  How?  Naaah, you'd never.",
    no_arg_room = "$n spanks the thin air with a flat hand.",
    found_char = "You spank $M vigorously, long and hard.  Your hand hurts.",
    found_room = "$n spanks $N over $s knee.  It hurts to even watch.",
    found_victim = "$n spanks you long and hard.  You feel like a naughty child.",
    not_found = "Are you sure about this?  I mean, that person isn't even here!",
    self_char = "Hmm, not likely.",
}

Socials["spit"] = {
    min_victim_pos = 0,
    no_arg_char = "You spit over your left shoulder.",
    no_arg_room = "$n spits over $s left shoulder.",
    found_char = "You spit on $M.",
    found_room = "$n spits in $N's face.",
    found_victim = "$n spits in your face.",
    not_found = "Can you spit that far?",
    self_char = "You drool down your front.",
    self_room = "$n drools down $s front.",
}

Socials["squeeze"] = {
    min_victim_pos = 0,
    no_arg_char = "Where, what, how, WHO???",
}

Socials["stare"] = {
    min_victim_pos = 0,
    no_arg_char = "You stare at the sky.",
    no_arg_room = "$n stares at the sky.",
    found_char = "You stare dreamily at $N, completely lost in $S eyes..",
    found_room = "$n stares dreamily at $N.",
    found_victim = "$n stares dreamily at you, completely lost in your eyes.",
    not_found = "You stare and stare but can't see that person anywhere...",
    self_char = "You stare dreamily at yourself - enough narcissism for now.",
    self_room = "$n stares dreamily at $mself - NARCISSIST!",
}

Socials["steam"] = {
    min_victim_pos = 0,
    no_arg_char = "You let out some steam, much to the others' relief (and your own!)",
    no_arg_room = "$n lets out a lot of steam, much to your relief.",
}

Socials["stroke"] = {
    min_victim_pos = 0,
    no_arg_char = "Whose thigh would you like to stroke?",
}

Socials["strut"] = {
    min_victim_pos = 0,
    no_arg_char = "Strut your stuff.",
    no_arg_room = "$n struts proudly.",
}

Socials["sulk"] = {
    min_victim_pos = 1,
    no_arg_char = "You sulk.",
    no_arg_room = "$n sulks in the corner.",
}

Socials["tackle"] = {
    min_victim_pos = 0,
    no_arg_char = "You tackle the air.  It stands not a chance.",
    no_arg_room = "$n starts running around $mself in a desparate attempt to tackle the air.",
    found_char = "You ruthlessly tackle $M to the ground.",
    found_room = "$n ruthlessly tackles $N, pinning $M to the ground.",
    found_victim = "$n suddenly lunges at you and tackles you to the ground!",
    not_found = "That person isn't here (luck for them, it would seem...)",
    self_char = "Tackle yourself?  Yeah, right....",
    self_room = "$n makes a dextrous move and kicks $s left leg away with $s right.",
}

Socials["tango"] = {
    min_victim_pos = 0,
    no_arg_char = "With whom would you like to tango?",
    no_arg_room = "$n puts a rose between $s teeth, but takes out it since noone joins $m.",
    found_char = "You put a rose between your teeth and tango with $M seductively.",
    found_room = "$n puts a rose between $s teeth and tangos with $N seductively.",
    found_victim = "$n puts a rose between $s teeth and tangos with you seductively.",
    not_found = "That person isn't around.  Better sit this one out.",
    self_char = "Feels rather stupid, doesn't it?",
    self_room = "$n puts a rose between $s teeth and tries to tango with $mself.",
}

Socials["taunt"] = {
    min_victim_pos = 0,
    no_arg_char = "You taunt the nothing in front of you.",
    no_arg_room = "$n taunts something that seems to be right in front of $m.",
    found_char = "You taunt $M, to your own delight.",
    found_room = "$n taunts $N rather insultingly.  $n seems to enjoy it tremendously.",
    found_victim = "$n taunts you.  It really hurts your feelings.",
    not_found = "Hmmmmmmm.....nope, no one by that name here.",
    self_char = "You taunt yourself, almost making you cry...:(",
    self_room = "$n taunts $mself to tears.",
}

Socials["thank"] = {
    min_victim_pos = 0,
    no_arg_char = "Thank you too.",
}

Socials["think"] = {
    min_victim_pos = 1,
    no_arg_char = "You think about life, the universe and everything.",
    no_arg_room = "$n sinks deeply into thought about the meaning of life.",
    found_char = "You think about what purpose $E has in relation to your part of life.",
    found_room = "$n stops and thinks about $N, completely lost in thought.",
    found_victim = "Your ears burn as $n thinks about you.. you wonder what about.",
    not_found = "You'd better think harder, if you hope to make contact!",
    self_char = "You think about yourself (for once).",
    self_room = "$n thinks about $mself for a change.....(?)",
}

Socials["tickle"] = {
    min_victim_pos = 0,
    no_arg_char = "Who do you want to tickle??",
}

Socials["twiddle"] = {
    min_victim_pos = 0,
    no_arg_char = "You patiently twiddle your thumbs.",
    no_arg_room = "$n patiently twiddles $s thumbs.",
}

Socials["wave"] = {
    min_victim_pos = 0,
    no_arg_char = "You wave.",
    no_arg_room = "$n waves happily.",
    found_char = "You wave goodbye to $N.",
    found_room = "$n waves goodbye to $N.",
    found_victim = "$n waves goodbye to you.  Have a good journey.",
    not_found = "They didn't wait for you to wave goodbye.",
    self_char = "Are you going on adventures as well??",
    self_room = "$n waves goodbye to $mself.",
}

Socials["whine"] = {
    min_victim_pos = 0,
    no_arg_char = "You whine pitifully.",
    no_arg_room = "$n whines pitifully about the whole situation.",
}

Socials["whistle"] = {
    min_victim_pos = 0,
    no_arg_char = "You whistle appreciatively.",
    no_arg_room = "$n whistles appreciatively.",
}

Socials["wiggle"] = {
    min_victim_pos = 0,
    no_arg_char = "Your wiggle your bottom.",
    no_arg_room = "$n wiggles $s bottom.",
}

Socials["wink"] = {
    min_victim_pos = 0,
    no_arg_char = "Have you got something in your eye?",
    no_arg_room = "$n winks suggestively.",
    found_char = "You wink suggestively at $N.",
    found_room = "$n winks at $N.",
    found_victim = "$n winks suggestively at you.",
    not_found = "No one with that name is present.",
    self_char = "You wink at yourself?? -- what are you up to?",
    self_room = "$n winks at $mself -- something strange is going on...",
}

Socials["worship"] = {
    min_victim_pos = 0,
    no_arg_char = "You find yourself head-down in the dirt, worshipping.",
    no_arg_room = "$n starts worshipping nothing at all.",
    found_char = "You fall to your knees and worship $M deeply.",
    found_room = "$n falls to $s knees, worshipping $N with uncanny dedication.",
    found_victim = "$n kneels before you in solemn worship.",
    not_found = "Uh.. who?  They're not here, pal.",
    self_char = "You seem sure to have found a true deity.....",
    self_room = "$n falls to $s knees and humbly worships $mself.",
}

Socials["yawn"] = {
    min_victim_pos = 0,
    no_arg_char = "Gosh, will you trade those teeth for mine?? -- you get my glasseyes in the bargain too!",
    no_arg_room = "$n yawns.",
}

Socials["yodel"] = {
    min_victim_pos = 0,
    no_arg_char = "You start yodelling loudly and rather beautifully in your own ears.",
    no_arg_room = "$n starts a yodelling session that goes right to the bone.",
}

return Socials
