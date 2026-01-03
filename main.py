import argparse
import os
from dotenv import load_dotenv
from ai_utils import generate_alt_text
from social_utils import post_to_mastodon, post_to_instagram

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Auto Social Poster")
    parser.add_argument("image", help="Path to the image file")
    parser.add_argument("--caption", "-c", required=True, help="Caption for the post")
    parser.add_argument("--provider", "-p", choices=["openai", "gemini", "moondream"], default="gemini", help="AI provider for alt-text")
    parser.add_argument("--post-to", choices=["mastodon", "instagram", "all"], default="mastodon", help="Platform(s) to post to")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt and post immediately")
    parser.add_argument("--no-post", action="store_true", help="Generate alt-text only, do not post")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.image):
        print(f"Error: Image not found at {args.image}")
        return

    print(f"Generating alt-text using {args.provider}...")
    try:
        alt_text = generate_alt_text(args.image, args.provider)
        print("\nGenerated Alt-Text:")
        print("-" * 40)
        print(alt_text)
        print("-" * 40)
    except Exception as e:
        print(f"Error generating alt-text: {e}")
        return

    if args.no_post:
        print("Skipping posting as requested.")
        return

    if not args.yes:
        confirm = input("Proceed with posting? (y/n): ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return

    if args.post_to == "mastodon" or args.post_to == "all":
        post_to_mastodon(args.image, args.caption, alt_text)
    
    if args.post_to == "instagram" or args.post_to == "all":
        post_to_instagram(args.image, args.caption, alt_text)

if __name__ == "__main__":
    main()
