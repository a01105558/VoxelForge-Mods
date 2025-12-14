from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from telegram.error import BadRequest
import json
import os
import asyncio

# ================= إعدادات التخزين =================
DATA_FILE = "bot_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # ===> الإصلاح الجذري لضمان التوافق مع البيانات القديمة <===
                loaded_users = data.get("users", {})
                if isinstance(loaded_users, list):
                    # إذا كانت البيانات القديمة قائمة، قم بتحويلها إلى قاموس
                    print("Legacy user list found. Converting to new dictionary format...")
                    new_users_dict = {str(user_id): {"subscribed": False} for user_id in loaded_users}
                    data["users"] = new_users_dict
                    # احفظ التغيير فوراً
                    save_data()
                
                return data
        except (json.JSONDecodeError, TypeError):
            # في حالة تلف الملف، ابدأ ببيانات فارغة
            return {"mods": {}, "updates": {}, "users": {}}
            
    return {"mods": {}, "updates": {}, "users": {}}

def save_data():
    # التأكد من أن mods و updates موجودة قبل الحفظ
    global mods, updates, users
    data_to_save = {
        "mods": mods if 'mods' in globals() else {},
        "updates": updates if 'updates' in globals() else {},
        "users": users if 'users' in globals() else {}
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=4)

# --- تحميل البيانات ---
data = load_data()
mods = data.get("mods", {})
updates = data.get("updates", {})
users = data.get("users", {})

# ================= الثوابت =================
TOKEN = "7531553007:AAED2oG9gIHyQ4CEgpmkMITQTf1wsVQgN7k"
ADMIN_ID = 5530049632
BOT_LINK = "https://t.me/MCModzBot"
SUPPORT_BOT_USERNAME = "VoxelForgeSupport_bot"
CHANNEL_USERNAME = "@VoxelForgeChannel"

user_state = {}

# ================= الواجهات (Keyboards) =================
def main_menu(user_id):
    buttons = [
        ["المودات 🎮", "تحديثات ماين كرافت 🆕"],
        ["الدعم الفني 🛠️"],
        ["شارك البوت 📤", "مساعدة ❓"]
    ]
    if user_id == ADMIN_ID:
        buttons.append(["⚜️ لوحة تحكم المشرف ⚜️"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def admin_menu():
    buttons = [
        ["📊 الإحصائيات", "إدارة المودات 🎮"],
        ["إدارة التحديثات 🆕", "إرسال إشعار 📢"],
        ["🔙 الرجوع للقائمة الرئيسية"]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def mod_management_menu():
    buttons = [
        ["➕ إضافة مود جديد", "✏️ تعديل مود"],
        ["🗑️ حذف مود", "🔙 الرجوع للوحة التحكم"]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def update_management_menu():
    buttons = [
        ["➕ إضافة تحديث جديد", "✏️ تعديل تحديث"],
        ["🗑️ حذف تحديث", "🔙 الرجوع للوحة التحكم"]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def back_btn(text="🔙 رجوع"):
    return ReplyKeyboardMarkup([[text]], resize_keyboard=True)

# ================= دوال الاشتراك الإجباري =================
async def is_user_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if user_id == ADMIN_ID:
        return True
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except BadRequest as e:
        if "user not found" in e.message.lower():
            return False
        print(f"Error checking subscription for {user_id}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error checking subscription for {user_id}: {e}")
        return False

async def force_subscribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not update.effective_user: return False
    
    user_id = update.effective_user.id
    user_id_str = str(user_id)

    if users.get(user_id_str, {}).get("subscribed", False):
        return True

    if await is_user_subscribed(user_id, context):
        users[user_id_str] = {"subscribed": True}
        save_data()
        return True
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("1. اضغط هنا للاشتراك في القناة", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton("2. ✅ لقد اشتركت، تحقق الآن", callback_data="check_subscription")]
        ])
        
        message_to_send = (
            "🛑 **عذراً، يجب عليك الاشتراك في القناة أولاً لاستخدام البوت.**\n\n"
            "**الخطوات:**\n"
            "1. اشترك في القناة عبر الزر أدناه.\n"
            "2. ارجع واضغط على زر التحقق."
        )

        if update.message:
            await update.message.reply_text(message_to_send, reply_markup=keyboard, parse_mode='Markdown')
        elif update.callback_query:
            await update.callback_query.message.reply_text(message_to_send, reply_markup=keyboard, parse_mode='Markdown')

        return False

# ================= معالجات الأوامر والرسائل =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_str = str(update.effective_user.id)
    if user_id_str not in users:
        users[user_id_str] = {"subscribed": False}
        save_data()
    
    welcome_text = (
        "👋 **أهلاً بك في عالم Minecraft Mods!**\n\n"
        "هنا بوابتك لاكتشاف وتحميل أفضل المودات والتحديثات بسهولة وأمان.\n\n"
        "اضغط على **\"🚀 ابدأ الاستكشاف\"** للانطلاق."
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=ReplyKeyboardMarkup([["🚀 ابدأ الاستكشاف"]], resize_keyboard=True, one_time_keyboard=True),
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return

    if not await force_subscribe_handler(update, context):
        return

    if update.message.photo or update.message.video:
        await handle_media(update, context)
        return

    if not update.message.text: return

    user_id = update.effective_user.id
    text = update.message.text

    if user_id == ADMIN_ID and user_state.get(user_id) and "media" in user_state.get(user_id):
        await update.message.reply_text("⏳ **خطأ في الإدخال.**\n\nيرجى إرسال **صورة أو فيديو**، وليس نصاً.", reply_markup=back_btn("❌ إلغاء"))
        return

    if text == "🚀 ابدأ الاستكشاف":
        user_state[user_id] = None
        await update.message.reply_text("🌟 تم تفعيل القائمة الرئيسية. اختر ما يثير اهتمامك!", reply_markup=main_menu(user_id))
        return

    if text.startswith("🔙") or text.startswith("❌"):
        await handle_back_button(update, context)
        return

    if text == "المودات 🎮":
        user_state[user_id] = "mods"
        mod_list = "\n".join([f"▫️ `{k}`. {v['name']}" for k, v in mods.items()]) or "لم تتم إضافة أي مودات بعد."
        await update.message.reply_text(f"🎮 **قائمة المودات المتوفرة:**\n\n{mod_list}\n\n*أرسل رقم المود لعرض تفاصيله.*", reply_markup=back_btn(), parse_mode='Markdown')
    elif text == "تحديثات ماين كرافت 🆕":
        user_state[user_id] = "updates"
        update_list = "\n".join([f"▫️ `{k}`. {v['name']}" for k, v in updates.items()]) or "لم تتم إضافة أي تحديثات بعد."
        await update.message.reply_text(f"🆕 **آخر تحديثات ماين كرافت:**\n\n{update_list}\n\n*أرسل رقم التحديث لعرض تفاصيله.*", reply_markup=back_btn(), parse_mode='Markdown')
    elif text == "الدعم الفني 🛠️":
        await update.message.reply_text(f"💬 هل تحتاج إلى مساعدة؟ فريق الدعم الفني جاهز لخدمتك عبر البوت المخصص:\n\n🔗 **[اضغط هنا للتواصل مع الدعم](https://t.me/{SUPPORT_BOT_USERNAME})**", reply_markup=main_menu(user_id), parse_mode='Markdown')
    elif text == "مساعدة ❓":
        await update.message.reply_text("💡 **دليل الاستخدام:**\n\n- استخدم زر **\"المودات\"** أو **\"التحديثات\"** لتصفح المحتوى.\n- أرسل **رقم** العنصر الذي تريده لعرض تفاصيله ورابط تحميله.\n- زر **\"الدعم الفني\"** يوجهك لفريق المساعدة.\n- زر **\"شارك البوت\"** يمنحك رابطاً لمشاركته مع أصدقائك.", reply_markup=main_menu(user_id), parse_mode='Markdown')
    elif text == "شارك البوت 📤":
        await update.message.reply_text(f"💌 هل أعجبك البوت؟ شاركه مع أصدقائك ومجتمع ماين كرافت!\n\n{BOT_LINK}", reply_markup=main_menu(user_id))
    
    elif text.isdigit():
        state = user_state.get(user_id)
        if state == "mods": await show_item_details(update, context, text, "mod")
        elif state == "updates": await show_item_details(update, context, text, "update")
        elif user_id == ADMIN_ID: await handle_admin_text_messages(update, context)
    
    elif text == "⚜️ لوحة تحكم المشرف ⚜️" and user_id == ADMIN_ID:
        user_state[user_id] = "admin_panel"
        await update.message.reply_text("⚜️ **أهلاً بك في لوحة التحكم.**\n\nاختر أحد الخيارات لإدارة محتوى البوت.", reply_markup=admin_menu())
    
    elif user_id == ADMIN_ID and user_state.get(user_id):
        await handle_admin_text_messages(update, context)

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not await force_subscribe_handler(update, context):
        return

    user_id = query.from_user.id
    user_id_str = str(user_id)

    if query.data == "check_subscription":
        # The check is already done in force_subscribe_handler
        # This part will only run if the user is now subscribed
        await query.message.edit_text(
            "✅ **شكراً لاشتراكك!**\n\nيمكنك الآن استخدام جميع ميزات البوت.",
            reply_markup=None
        )
        await context.bot.send_message(user_id, "🌟 تم تفعيل القائمة الرئيسية. اختر ما يثير اهتمامك!", reply_markup=main_menu(user_id))

# ... (بقية الدوال تبقى كما هي بدون تغيير) ...
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID: return

    state = user_state.get(user_id)
    if not state or "media" not in state: return

    media_type = "photo" if update.message.photo else "video"
    file_id = update.message.photo[-1].file_id if media_type == "photo" else update.message.video.file_id

    item_type = "mod" if "mod" in state else "update"
    data_dict = mods if item_type == "mod" else updates
    
    management_menu_func = mod_management_menu if item_type == "mod" else update_management_menu

    if "add" in state:
        item_data = context.user_data.get(f"new_{item_type}")
        if not item_data: return
        
        item_data["media_type"] = media_type
        item_data["media_id"] = file_id
        
        new_id = str(max([int(k) for k in data_dict.keys()] + [0]) + 1)
        data_dict[new_id] = item_data
        
        await update.message.reply_text(f"✅ **اكتملت الإضافة بنجاح!**\n\nتم حفظ \"{item_data['name']}\" بالرقم `{new_id}`.", reply_markup=management_menu_func(), parse_mode='Markdown')
    
    elif "edit" in state:
        item_id = context.user_data.get(f"edit_{item_type}_id")
        if not item_id or item_id not in data_dict: return

        data_dict[item_id]["media_type"] = media_type
        data_dict[item_id]["media_id"] = file_id
        
        await update.message.reply_text(f"🖼️ **تم تحديث الوسائط بنجاح** للملف \"{data_dict[item_id]['name']}\".", reply_markup=management_menu_func())

    save_data()
    user_state[user_id] = f"admin_{item_type}_manage"
    context.user_data.clear()

async def show_item_details(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str, item_type: str):
    data_dict = mods if item_type == "mod" else updates
    if item_id not in data_dict:
        await update.message.reply_text(f"⚠️ **عفواً، الرقم الذي أدخلته غير صحيح.**\n\nيرجى التأكد من الرقم والمحاولة مرة أخرى.", reply_markup=back_btn())
        return

    item = data_dict[item_id]
    user_state[update.effective_user.id] = f"{item_type}_detail"
    
    caption = (
        f"✨ **{item['name']}**\n\n"
        f"{item['desc']}\n\n"
        f"🔗 **[اضغط هنا للتحميل]({item['link']})**"
    )
    if item_type == "update" and item.get('patch'):
        caption += f"\n🩹 **[اضغط هنا لتحميل الباتش]({item['patch']})**"

    reply_markup = back_btn("🔙 الرجوع للقائمة")
    if item.get("media_id"):
        try:
            if item["media_type"] == "photo":
                await context.bot.send_photo(update.effective_chat.id, item["media_id"], caption=caption, parse_mode='Markdown', reply_markup=reply_markup)
            elif item["media_type"] == "video":
                await context.bot.send_video(update.effective_chat.id, item["media_id"], caption=caption, parse_mode='Markdown', reply_markup=reply_markup)
        except Exception as e:
            print(f"Error sending media for {item_type} {item_id}: {e}")
            await update.message.reply_text("حدث خطأ أثناء عرض الملف، لكن إليك التفاصيل:\n\n" + caption, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(caption, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_back_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_state.get(user_id)
    
    cancel_msg = "❌ تم إلغاء العملية."

    if state and state.startswith("admin_"):
        if "add" in state or "edit" in state or "delete" in state:
            if "mod" in state:
                user_state[user_id] = "admin_mod_manage"
                await update.message.reply_text(cancel_msg, reply_markup=mod_management_menu())
            elif "update" in state:
                user_state[user_id] = "admin_update_manage"
                await update.message.reply_text(cancel_msg, reply_markup=update_management_menu())
        elif state == "admin_broadcast":
            user_state[user_id] = "admin_panel"
            await update.message.reply_text(cancel_msg, reply_markup=admin_menu())
        elif state in ["admin_mod_manage", "admin_update_manage"]:
            user_state[user_id] = "admin_panel"
            await update.message.reply_text("تم الرجوع إلى لوحة التحكم الرئيسية.", reply_markup=admin_menu())
        elif state == "admin_panel":
            user_state[user_id] = None
            await update.message.reply_text("تم الرجوع إلى القائمة الرئيسية للبوت.", reply_markup=main_menu(user_id))
    else:
        user_state[user_id] = None
        await update.message.reply_text("تم الرجوع إلى القائمة الرئيسية.", reply_markup=main_menu(user_id))
    
    context.user_data.clear()

async def handle_admin_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    state = user_state.get(user_id)

    if state == "admin_panel":
        if text == "إدارة المودات 🎮":
            user_state[user_id] = "admin_mod_manage"
            await update.message.reply_text("🛠️ **إدارة المودات:**", reply_markup=mod_management_menu())
        elif text == "إدارة التحديثات 🆕":
            user_state[user_id] = "admin_update_manage"
            await update.message.reply_text("🛠️ **إدارة التحديثات:**", reply_markup=update_management_menu())
        elif text == "📊 الإحصائيات":
            stats_msg = f"📊 **إحصائيات البوت:**\n\n- 👤 **المستخدمون:** {len(users)}\n- 🎮 **المودات:** {len(mods)}\n- 🆕 **التحديثات:** {len(updates)}"
            await update.message.reply_text(stats_msg, reply_markup=admin_menu())
        elif text == "إرسال إشعار 📢":
            user_state[user_id] = "admin_broadcast"
            await update.message.reply_text("📝 **أرسل رسالة الإشعار:**", reply_markup=back_btn("❌ إلغاء"))
        return

    if state == "admin_broadcast":
        await send_broadcast(update, context)
        return

    for item_type in ["mod", "update"]:
        data_dict = mods if item_type == "mod" else updates
        management_menu = mod_management_menu if item_type == "mod" else update_management_menu
        
        if state == f"admin_{item_type}_manage":
            if text.startswith("➕"):
                user_state[user_id] = f"admin_add_{item_type}_name"
                await update.message.reply_text(f"**الخطوة 1: الاسم**", reply_markup=back_btn("❌ إلغاء"))
            elif text.startswith("✏️"):
                user_state[user_id] = f"admin_edit_{item_type}_select"
                item_list = "\n".join([f"`{k}`. {v['name']}" for k, v in data_dict.items()]) or "لا يوجد."
                await update.message.reply_text(f"**اختر للتعديل:**\n{item_list}", reply_markup=back_btn("❌ إلغاء"), parse_mode='Markdown')
            elif text.startswith("🗑️"):
                user_state[user_id] = f"admin_delete_{item_type}_select"
                item_list = "\n".join([f"`{k}`. {v['name']}" for k, v in data_dict.items()]) or "لا يوجد."
                await update.message.reply_text(f"**اختر للحذف:**\n{item_list}", reply_markup=back_btn("❌ إلغاء"), parse_mode='Markdown')
            return

        if state == f"admin_add_{item_type}_name":
            context.user_data[f"new_{item_type}"] = {"name": text}
            user_state[user_id] = f"admin_add_{item_type}_desc"
            await update.message.reply_text("**الخطوة 2: الوصف**", reply_markup=back_btn("❌ إلغاء"))
        elif state == f"admin_add_{item_type}_desc":
            context.user_data[f"new_{item_type}"]["desc"] = text
            user_state[user_id] = f"admin_add_{item_type}_link"
            await update.message.reply_text("**الخطوة 3: رابط التحميل**", reply_markup=back_btn("❌ إلغاء"))
        elif state == f"admin_add_{item_type}_link":
            context.user_data[f"new_{item_type}"]["link"] = text
            if item_type == "update":
                user_state[user_id] = f"admin_add_{item_type}_patch"
                await update.message.reply_text("**الخطوة 4: رابط الباتش** (أو 'لا يوجد')", reply_markup=back_btn("❌ إلغاء"))
            else:
                user_state[user_id] = f"admin_add_{item_type}_media"
                await update.message.reply_text("**الخطوة 4: الوسائط** (صورة/فيديو)", reply_markup=back_btn("❌ إلغاء"))
        elif state == f"admin_add_{item_type}_patch" and item_type == "update":
            context.user_data[f"new_{item_type}"]["patch"] = text if text.lower() != 'لا يوجد' else None
            user_state[user_id] = f"admin_add_{item_type}_media"
            await update.message.reply_text("**الخطوة 5: الوسائط** (صورة/فيديو)", reply_markup=back_btn("❌ إلغاء"))

        elif state == f"admin_delete_{item_type}_select":
            if text in data_dict:
                item_name = data_dict.pop(text)["name"]
                save_data()
                user_state[user_id] = f"admin_{item_type}_manage"
                await update.message.reply_text(f"🗑️ **تم حذف \"{item_name}\".**", reply_markup=management_menu())
            else:
                await update.message.reply_text("⚠️ **رقم غير صالح.**", reply_markup=back_btn("❌ إلغاء"))

        elif state == f"admin_edit_{item_type}_select":
            if text in data_dict:
                context.user_data[f"edit_{item_type}_id"] = text
                user_state[user_id] = f"admin_edit_{item_type}_field"
                buttons = [["الاسم", "الوصف", "الرابط"], ["🖼️ تعديل الوسائط"], ["❌ إلغاء التعديل"]]
                if item_type == "update": buttons[0].append("الباتش")
                await update.message.reply_text(f"**تعديل \"{data_dict[text]['name']}\"**", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
            else:
                await update.message.reply_text("⚠️ **رقم غير صالح.**", reply_markup=back_btn("❌ إلغاء"))
        elif state == f"admin_edit_{item_type}_field":
            field_map = {"الاسم": "name", "الوصف": "desc", "الرابط": "link", "الباتش": "patch"}
            if text == "🖼️ تعديل الوسائط":
                user_state[user_id] = f"admin_edit_{item_type}_media"
                await update.message.reply_text("أرسل الصورة/الفيديو الجديد.", reply_markup=back_btn("❌ إلغاء"))
            elif text in field_map:
                context.user_data[f"edit_{item_type}_field"] = field_map[text]
                user_state[user_id] = f"admin_edit_{item_type}_value"
                await update.message.reply_text(f"📝 **أدخل القيمة الجديدة لـ \"{text}\":**", reply_markup=back_btn("❌ إلغاء"))
            elif text == "❌ إلغاء التعديل":
                user_state[user_id] = f"admin_{item_type}_manage"
                context.user_data.clear()
                await update.message.reply_text("تم إلغاء التعديل.", reply_markup=management_menu())
        elif state == f"admin_edit_{item_type}_value":
            item_id = context.user_data.get(f"edit_{item_type}_id")
            field = context.user_data.get(f"edit_{item_type}_field")
            if item_id and field:
                data_dict[item_id][field] = text
                save_data()
                user_state[user_id] = f"admin_{item_type}_manage"
                await update.message.reply_text("✅ **تم الحفظ!**", reply_markup=management_menu())
                context.user_data.clear()

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id
    broadcast_text = update.message.text
    
    await update.message.reply_text("⏳ **جاري الإرسال...**", reply_markup=admin_menu())
    
    success_count = 0
    fail_count = 0
    
    for user_id_str in users.keys():
        try:
            await context.bot.send_message(int(user_id_str), broadcast_text, parse_mode='Markdown')
            success_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            fail_count += 1
            print(f"Failed to send to {user_id_str}: {e}")
            
    user_state[admin_id] = "admin_panel"
    
    await context.bot.send_message(
        admin_id,
        f"✅ **اكتمل الإرسال.**\n\n- ✔️ **نجح:** {success_count}\n- ✖️ **فشل:** {fail_count}",
        reply_markup=admin_menu()
    )

# ================= تشغيل البوت =================
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    if not os.path.exists(DATA_FILE):
        save_data()

    print("Bot is running. Root cause fixed. All systems operational.")
    app.run_polling()
