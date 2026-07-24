from __future__ import annotations

from pathlib import Path

import requests

import config


TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramChatMigratedError(RuntimeError):
	def __init__(self, migrated_chat_id: int) -> None:
		super().__init__(f"Telegram chat migrated to {migrated_chat_id}")
		self.migrated_chat_id = migrated_chat_id


def _request_json(method: str, url: str, timeout: int = 30, **kwargs) -> dict:
	response = requests.request(method, url, timeout=timeout, **kwargs)

	try:
		payload = response.json()
	except ValueError as exc:
		if not response.ok:
			message = response.text.strip()
			raise RuntimeError(f"Telegram API request failed with status {response.status_code}: {message}") from exc
		raise RuntimeError("Telegram API returned a non-JSON response") from exc

	if not payload.get("ok", False):
		parameters = payload.get("parameters") or {}
		migrated_chat_id = parameters.get("migrate_to_chat_id")
		if migrated_chat_id is not None:
			raise TelegramChatMigratedError(int(migrated_chat_id))

		message = payload.get("description") or f"Telegram API error: {payload}"
		raise RuntimeError(message)

	return payload


def _validate_inputs(image_paths: list[str | Path], birthday_names: list[str]) -> None:
	if len(image_paths) != len(birthday_names):
		raise ValueError("image_paths and birthday_names must have the same length")


def send_posters_to_telegram(image_paths: list[str | Path], birthday_names: list[str]) -> bool:
	_validate_inputs(image_paths, birthday_names)

	names_text = "\n".join(birthday_names) if birthday_names else "None"
	message_text = (
		"🎉 Gradient Birthday Alert\n\n"
		"Today's Birthday(s):\n"
		f"{names_text}\n\n"
		"Please review the attached poster(s) and post them on Instagram.\n\n"
		"Generated automatically by Gradient Automation."
	)

	base_url = f"{TELEGRAM_API_BASE}/bot{config.BOT_TOKEN}"
	chat_id = config.CHAT_ID

	def _send_message(current_chat_id: str | int) -> None:
		_request_json(
			"POST",
			f"{base_url}/sendMessage",
			data={"chat_id": current_chat_id, "text": message_text},
		)

	def _send_photo(current_chat_id: str | int, path: Path) -> None:
		with path.open("rb") as image_file:
			_request_json(
				"POST",
				f"{base_url}/sendPhoto",
				data={"chat_id": current_chat_id},
				files={"photo": (path.name, image_file, "image/png")},
				timeout=120,
			)

	try:
		_send_message(chat_id)
	except TelegramChatMigratedError as exc:
		chat_id = exc.migrated_chat_id
		_send_message(chat_id)

	failed_uploads: list[str] = []
	for image_path in image_paths:
		path = Path(image_path)
		if not path.exists():
			failed_uploads.append(str(path))
			print(f"Skipping missing poster: {path}")
			continue

		print(f"Uploading poster: {path.name}")

		try:
			_send_photo(chat_id, path)
		except TelegramChatMigratedError as exc:
			chat_id = exc.migrated_chat_id
			try:
				_send_photo(chat_id, path)
			except Exception as retry_exc:
				failed_uploads.append(str(path))
				print(f"Failed to upload {path.name}: {retry_exc}")
				continue
		except Exception as exc:
			failed_uploads.append(str(path))
			print(f"Failed to upload {path.name}: {exc}")
			continue

		print(f"Successfully uploaded {path.name}")

	if failed_uploads:
		raise RuntimeError(f"Failed to upload {len(failed_uploads)} poster(s): {', '.join(failed_uploads)}")

	return True