import json

STORIES = [
    {
        "title": "The Lion and the Mouse",
        "moral": "No act of kindness is ever wasted.",
        "learning": "Always be kind to everyone, no matter how small. Even the tiniest friend can help you in the biggest way!",
        "style": "bright colorful Pixar-style 3D animation",
        "char_desc": "A massive male lion with a thick dark-brown mane and a tiny grey field mouse",
        "scenes": [
            ("A mighty lion was napping when a little mouse ran over his nose!",
             "Deep in the vibrant jungle, a mighty and majestic lion was enjoying a peaceful afternoon nap in the sun. Suddenly, without looking where he was going, a tiny grey field mouse ran right over the sleeping giant's enormous nose!",
             "the mouse running over the nose of the sleeping lion"),
            
            ("The lion trapped the mouse! The mouse cried, \"Please let me go! I will help you one day!\"",
             "ROAR! The angry lion woke up with a massive start, instantly trapping the tiny mouse beneath his heavy paw. The terrified little mouse looked up and squeaked with all his might, \"Please, oh please king of the jungle, spare my life! If you let me go, I promise that one day I will repay your kindness and help you!\"",
             "the lion roaring loudly, trapping the mouse under his giant paw"),
            
            ("The lion laughed, \"You? Help me?\" But he kindly let the mouse run away.",
             "The mighty lion stopped roaring and stared down at the tiny creature. He threw his head back and laughed a huge belly laugh! \"A tiny thing like you? Help a massive king like me?\" he chuckled. Even though it seemed silly, the lion felt generous that day, so he lifted his heavy paw and let the tiny mouse scamper into the bushes.",
             "the lion laughing out loud, lifting his paw to let the mouse run away"),
            
            ("Days later, the huge lion was trapped in a hunter's thick rope net! He roared for help!",
             "Many sunny days passed. One afternoon, while hunting for food, the lion accidentally stepped into a hidden trap! WHOOSH! A massive, thick rope net swung up into the air, tangling the lion completely. The helpless beast roared and roared, \"Help! Somebody please help me!\" but no big animals dared to come near.",
             "the lion trapped tightly inside a heavy rope net, looking scared"),
            
            ("The tiny mouse heard him! He quickly chewed through the ropes and set the giant lion free!",
             "Far away in the bushes, the tiny mouse recognized the roar of his old friend. He ran as fast as his little legs could carry him! Seeing the trapped king, the brave mouse climbed up the side of the net and started chewing furiously with his sharp little teeth. Snap! Snap! Snap! The thick ropes broke one by one, and the majestic lion was finally free, forever thankful to his tiny friend.",
              "the mouse chewing through the thick ropes with his teeth, freeing the happy lion"),
        ]
    }
]

MORALS_BASE = [
    "kids story", "moral story", "bedtime story", "children story",
    "animated story", "story for kids", "life lesson", "short story"
]

bank = []
for i, story in enumerate(STORIES):
    title = story["title"]
    moral = story["moral"]
    learning = story["learning"]
    char_desc = story["char_desc"]
    style = story["style"]

    scenes_data = []

# ── TITLE SCENE (first) ─────────────────────────────
    first_visual = story["scenes"][0][2]
    title_prompt = f"{char_desc}, {first_visual}, {style}, child-friendly, no text, 4k quality"
    
    scenes_data.append({
        "short_narration": f"This is the story of... {title}!",
        "long_narration": f"Welcome everyone! Today, we are going to tell you the wonderful and exciting story of... {title}!",
        "image_prompt": title_prompt
    })

    # ── STORY SCENES (middle) ───────────────────────────
    for short_nar, long_nar, visual_action in story["scenes"]:
        prompt = f"{char_desc}, {visual_action}, {style}, child-friendly, no text, 4k quality"
        scenes_data.append({
            "short_narration": short_nar,
            "long_narration": long_nar,
            "image_prompt": prompt
        })

    # ── LEARNING SCENE (last) ───────────────────────────
    last_visual = story["scenes"][-1][2]
    learning_prompt = f"{char_desc}, {last_visual}, {style}, child-friendly, no text, 4k quality"
    
    scenes_data.append({
        "short_narration": f"And the learning of this story is... {learning}",
        "long_narration": f"What an amazing adventure that was! Now, remember my friends, the learning of this story is... {learning}",
        "image_prompt": learning_prompt
    })

    desc = f"{title} | A fun animated moral story for kids!\\n\\nMoral: {moral}\\n\\n#Shorts #KidsStory #MoralStory #BedtimeStory #AnimatedStory"
    tags = MORALS_BASE + [title.lower(), moral.lower().rstrip(".")]

    bank.append({
        "id": i + 1,
        "title": title,
        "moral": moral,
        "scenes": scenes_data,
        "description": desc,
        "tags": tags
    })

with open("story_bank.json", "w", encoding="utf-8") as f:
    json.dump(bank, f, indent=2, ensure_ascii=False)

print(f"Created story_bank.json with {len(bank)} stories.")
