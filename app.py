from telethon import TelegramClient, events
import asyncio
import logging
from config import API_ID, API_HASH, SESSION_STRING, BOT_TOKEN
import os

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramMessageDeleter:
    def __init__(self):
        self.user_client = None
        self.bot_client = None
        self.bot_info = None

    async def start_user_client(self):
        """Start the user client using session string"""
        try:
            self.user_client = TelegramClient(
                session_string=SESSION_STRING,
                api_id=API_ID,
                api_hash=API_HASH
            )
            
            @self.user_client.on(events.NewMessage())
            async def handler(event):
                try:
                    # Ignore if no sender or not a group message
                    if not event.sender or not event.is_group:
                        return
                    
                    # Check if message is from a bot and not from our own bot
                    if (event.sender.bot and 
                        event.sender.id != self.bot_info.id):
                        
                        logger.info(f"🤖 Bot message detected from {event.sender.first_name} (ID: {event.sender.id})")
                        logger.info(f"📝 Message: {event.text[:100] if event.text else 'Media message'}")
                        
                        # Wait 10 seconds then delete
                        await asyncio.sleep(10)
                        
                        try:
                            await event.delete()
                            logger.info(f"✅ Successfully deleted bot message from {event.sender.first_name}")
                        except Exception as delete_error:
                            logger.error(f"❌ Failed to delete message: {delete_error}")
                            
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")

            await self.user_client.start()
            logger.info("✅ User client started successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to start user client: {e}")
            raise

    async def start_bot_client(self):
        """Start the bot client"""
        try:
            self.bot_client = TelegramClient(
                session='bot_session',
                api_id=API_ID, 
                api_hash=API_HASH
            ).start(bot_token=BOT_TOKEN)
            
            self.bot_info = await self.bot_client.get_me()
            logger.info(f"✅ Bot client started: {self.bot_info.first_name} (@{self.bot_info.username})")
            
            # Add start command handler
            @self.bot_client.on(events.NewMessage(pattern='/start'))
            async def start_handler(event):
                await event.reply("🤖 Bot Message Deleter is running!\n\nI will automatically delete other bot messages 10 seconds after they are sent.")
            
        except Exception as e:
            logger.error(f"❌ Failed to start bot client: {e}")
            raise

    async def check_connections(self):
        """Check if both clients are connected properly"""
        try:
            if self.user_client and self.bot_client:
                user_me = await self.user_client.get_me()
                bot_me = await self.bot_client.get_me()
                
                logger.info(f"🔗 User account: {user_me.first_name} (@{user_me.username})")
                logger.info(f"🔗 Bot account: {bot_me.first_name} (@{bot_me.username})")
                logger.info("✅ Both clients are connected and ready!")
                return True
        except Exception as e:
            logger.error(f"❌ Connection check failed: {e}")
            return False

    async def run(self):
        """Run both clients"""
        try:
            await self.start_bot_client()
            await self.start_user_client()
            
            if await self.check_connections():
                logger.info("🚀 Bot Message Deleter is now running!")
                logger.info("📝 Monitoring for bot messages...")
                
                # Keep the clients running
                await asyncio.gather(
                    self.user_client.run_until_disconnected(),
                    self.bot_client.run_until_disconnected()
                )
            else:
                logger.error("❌ Failed to establish connections")
                
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
        finally:
            # Cleanup
            if self.user_client:
                await self.user_client.disconnect()
            if self.bot_client:
                await self.bot_client.disconnect()

# For Heroku deployment
from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot Message Deleter is running!"

@app.route('/health')
def health():
    return "✅ Service is healthy"

async def start_bot():
    deleter = TelegramMessageDeleter()
    await deleter.run()

def run_bot():
    """Function to run the bot (for Heroku)"""
    asyncio.run(start_bot())

if __name__ == "__main__":
    # For local testing
    import threading
    
    # Start Flask app in a separate thread for Heroku
    flask_thread = threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False, use_reloader=False)
    )
    flask_thread.daemon = True
    flask_thread.start()
    
    # Start the bot
    run_bot()
