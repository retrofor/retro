from retrofor_wut import Bot

bot = Bot(hot_reload=True)
bot.load_adapters("retrofor_wut.adapter.cqhttp")

if __name__ == "__main__":
    bot.run()


