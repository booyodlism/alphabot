import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button, Select
import traceback
import os
from helpers.permissions import has_role

MAX_FIELDS = 20
COLOR_DEFAULT = discord.Color.blue()

ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID"))

def build_embed_page(data, color, fields, page, total_pages):
    embed = discord.Embed(
        title=data.get("title") or None,
        description=data.get("description") or None,
        color=color
    )
    embed.set_footer(text=f"Page {page+1}/{total_pages} • Powered by ALPHA™")

    thumbnail = data.get("thumbnail")
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    image = data.get("image")
    if image:
        embed.set_image(url=image)

    start = page * 5
    end = start + 5
    for field in fields[start:end]:
        embed.add_field(name=field["name"], value=field["value"], inline=False)
    return embed

def build_embed_without_page(data, color, fields):
    embed = discord.Embed(
        title=data.get("title") or None,
        description=data.get("description") or None,
        color=color
    )
    thumbnail = data.get("thumbnail")
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    image = data.get("image")
    if image:
        embed.set_image(url=image)
    for field in fields:
        embed.add_field(name=field["name"], value=field["value"], inline=False)
    embed.set_footer(text="Powered by ALPHA™")
    return embed

def admin_role_check():
    async def predicate(interaction: discord.Interaction):
        if not has_role(interaction.user, ADMIN_ROLE_ID):
            await interaction.response.send_message("❌ You must have the whitelist role to use this command.", ephemeral=True)
            print(f"[EmbedBuilderCog] Access denied for user {interaction.user} (ID: {interaction.user.id})")
            return False
        print(f"[EmbedBuilderCog] Access granted for user {interaction.user} (ID: {interaction.user.id})")
        return True
    return app_commands.check(predicate)

class EmbedMainModal(Modal):
    def __init__(self, view, initial_data=None):
        super().__init__(title="Embed Builder Main")
        self.view = view

        self.title_input = TextInput(label="Title", max_length=256, default=initial_data.get("title", "") if initial_data else "")
        self.description_input = TextInput(label="Description", style=discord.TextStyle.paragraph, max_length=1024, default=initial_data.get("description", "") if initial_data else "")
        self.thumbnail_input = TextInput(label="Thumbnail URL", max_length=1024, required=False, default=initial_data.get("thumbnail", "") if initial_data else "")
        self.image_input = TextInput(label="Image URL", max_length=1024, required=False, default=initial_data.get("image", "") if initial_data else "")

        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.thumbnail_input)
        self.add_item(self.image_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            print("[EmbedMainModal] Submitting modal")
            self.view.embed_data.update({
                "title": self.title_input.value,
                "description": self.description_input.value,
                "thumbnail": self.thumbnail_input.value,
                "image": self.image_input.value,
            })
            self.view.page = 0
            self.view.update_navigation_buttons()
            embed = self.view.get_embed()
            await interaction.response.edit_message(embed=embed, view=self.view)
            print("[EmbedMainModal] Preview updated after main info submit")
        except Exception as e:
            print("[EmbedMainModal] Error in on_submit:", e)
            traceback.print_exc()
            try:
                await interaction.response.send_message("⚠️ Error updating embed info.", ephemeral=True)
            except:
                pass

class AddFieldModal(Modal):
    def __init__(self, view):
        super().__init__(title="Add Embed Field")
        self.view = view

        self.name_input = TextInput(label="Field Name", max_length=256)
        self.value_input = TextInput(label="Field Value", style=discord.TextStyle.paragraph, max_length=1024)

        self.add_item(self.name_input)
        self.add_item(self.value_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            print("[AddFieldModal] Submitting modal")
            if len(self.view.fields) >= MAX_FIELDS:
                await interaction.response.send_message(f"⚠️ Maximum {MAX_FIELDS} fields reached.", ephemeral=True)
                print("[AddFieldModal] Max fields reached")
                return
            self.view.fields.append({
                "name": self.name_input.value,
                "value": self.value_input.value
            })
            self.view.total_pages = max(1, (len(self.view.fields) + 4) // 5)
            self.view.page = self.view.total_pages - 1
            self.view.update_navigation_buttons()
            embed = self.view.get_embed()
            await interaction.response.edit_message(embed=embed, view=self.view)
            print("[AddFieldModal] Preview updated after adding field")
        except Exception as e:
            print("[AddFieldModal] Error in on_submit:", e)
            traceback.print_exc()
            try:
                await interaction.response.send_message("⚠️ Error adding field.", ephemeral=True)
            except:
                pass

class EditFieldModal(Modal):
    def __init__(self, view, field_index: int):
        super().__init__(title="Edit Embed Field")
        self.view = view
        self.field_index = field_index

        field = self.view.fields[field_index]
        self.name_input = TextInput(label="Field Name", max_length=256, default=field["name"])
        self.value_input = TextInput(label="Field Value", style=discord.TextStyle.paragraph, max_length=1024, default=field["value"])

        self.add_item(self.name_input)
        self.add_item(self.value_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            print(f"[EditFieldModal] Editing field index {self.field_index}")
            self.view.fields[self.field_index] = {
                "name": self.name_input.value,
                "value": self.value_input.value
            }
            self.view.update_navigation_buttons()
            embed = self.view.get_embed()
            await interaction.response.edit_message(embed=embed, view=self.view)
            print("[EditFieldModal] Preview updated after editing field")
        except Exception as e:
            print("[EditFieldModal] Error editing field:", e)
            traceback.print_exc()
            try:
                await interaction.response.send_message("⚠️ Error editing field.", ephemeral=True)
            except:
                pass

class EditFieldSelect(Select):
    def __init__(self, view):
        options = []
        for idx, field in enumerate(view.fields):
            label = field["name"] if field["name"] else f"Field {idx+1}"
            if len(label) > 100:
                label = label[:97] + "..."
            options.append(discord.SelectOption(label=label, description=f"Field #{idx+1}", value=str(idx)))

        super().__init__(placeholder="Select a field to edit", min_values=1, max_values=1, options=options)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        selected_index = int(self.values[0])
        modal = EditFieldModal(self.view_ref, selected_index)
        await interaction.response.send_modal(modal)

class ColorSelect(Select):
    def __init__(self, view):
        options = [
            discord.SelectOption(label="Blue", description="Default blue color", value="blue"),
            discord.SelectOption(label="Green", description="Green color", value="green"),
            discord.SelectOption(label="Red", description="Red color", value="red"),
            discord.SelectOption(label="Purple", description="Purple color", value="purple"),
            discord.SelectOption(label="Orange", description="Orange color", value="orange"),
        ]
        super().__init__(placeholder="Select embed color", min_values=1, max_values=1, options=options)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        color_map = {
            "blue": discord.Color.blue(),
            "green": discord.Color.green(),
            "red": discord.Color.red(),
            "purple": discord.Color.purple(),
            "orange": discord.Color.orange(),
        }
        selected_color = color_map.get(self.values[0], discord.Color.blue())
        self.view_ref.color = selected_color
        self.view_ref.update_navigation_buttons()
        embed = self.view_ref.get_embed()
        await interaction.response.edit_message(embed=embed, view=self.view_ref)

class EmbedBuilderView(View):
    def __init__(self, cog, user_id):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = user_id
        self.embed_data = {
            "title": "",
            "description": "",
            "thumbnail": "",
            "image": "",
        }
        self.fields = []
        self.color = COLOR_DEFAULT
        self.page = 0
        self.total_pages = 1

        self.update_navigation_buttons()

    def update_navigation_buttons(self):
        self.total_pages = max(1, (len(self.fields) + 4) // 5)
        if self.page < 0:
            self.page = 0
        elif self.page >= self.total_pages:
            self.page = self.total_pages - 1

        self.prev_button.disabled = self.page == 0
        self.next_button.disabled = self.page == self.total_pages - 1

    def get_embed(self):
        return build_embed_page(self.embed_data, self.color, self.fields, self.page, self.total_pages)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not your session.", ephemeral=True)
            print(f"[EmbedBuilderView] Unauthorized user {interaction.user} tried to interact.")
            return False
        return True

    @discord.ui.button(label="Edit Main Info", style=discord.ButtonStyle.secondary)
    async def edit_main(self, interaction: discord.Interaction, button: Button):
        modal = EmbedMainModal(self, initial_data=self.embed_data)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Add Field", style=discord.ButtonStyle.primary)
    async def add_field(self, interaction: discord.Interaction, button: Button):
        if len(self.fields) >= MAX_FIELDS:
            await interaction.response.send_message(f"⚠️ Maximum {MAX_FIELDS} fields reached.", ephemeral=True)
            print("[EmbedBuilderView] Tried to add field but max reached.")
            return
        modal = AddFieldModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Edit Field", style=discord.ButtonStyle.secondary)
    async def edit_field_button(self, interaction: discord.Interaction, button: Button):
        if not self.fields:
            await interaction.response.send_message("⚠️ No fields to edit.", ephemeral=True)
            print("[EmbedBuilderView] Tried to edit field but no fields present.")
            return
        select = EditFieldSelect(self)
        temp_view = View()
        temp_view.add_item(select)
        await interaction.response.send_message("Select a field to edit:", view=temp_view, ephemeral=True)

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        if self.page > 0:
            self.page -= 1
            self.update_navigation_buttons()
            embed = self.get_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.page < self.total_pages - 1:
            self.page += 1
            self.update_navigation_buttons()
            embed = self.get_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Change Color", style=discord.ButtonStyle.primary)
    async def change_color_button(self, interaction: discord.Interaction, button: Button):
        select = ColorSelect(self)
        temp_view = View()
        temp_view.add_item(select)
        await interaction.response.send_message("Pilih warna embed:", view=temp_view, ephemeral=True)

    @discord.ui.button(label="Confirm Embed", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        try:
            if self.total_pages == 1:
                embed = build_embed_without_page(self.embed_data, self.color, self.fields)
                await interaction.channel.send(embed=embed)
            else:
                for p in range(self.total_pages):
                    embed = build_embed_page(self.embed_data, self.color, self.fields, p, self.total_pages)
                    await interaction.channel.send(embed=embed)
            await interaction.response.send_message("✅ Embed sent!", ephemeral=True)
            self.stop()
            print("[EmbedBuilderView] Embed sent and session stopped.")
        except Exception as e:
            print("[EmbedBuilderView] Failed to send embed:", e)
            traceback.print_exc()
            try:
                await interaction.response.send_message("⚠️ Failed to send embed.", ephemeral=True)
            except:
                pass

class EmbedBuilderCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="embedbuilder", description="Embed builder with interactive add field and color picker")
    @admin_role_check()
    async def embedbuilder(self, interaction: discord.Interaction):
        try:
            print(f"[EmbedBuilderCog] /embedbuilder invoked by user {interaction.user} (ID: {interaction.user.id})")
            view = EmbedBuilderView(self, interaction.user.id)
            embed = view.get_embed()
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            print("[EmbedBuilderCog] Started embed builder session")
        except Exception as e:
            print("[EmbedBuilderCog] Error starting embed builder:", e)
            traceback.print_exc()
            await interaction.response.send_message("⚠️ Failed to start embed builder.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(EmbedBuilderCog(bot))
