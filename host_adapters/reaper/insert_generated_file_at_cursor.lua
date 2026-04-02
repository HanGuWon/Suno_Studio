-- insert_generated_file_at_cursor.lua
-- Usage:
-- 1) Set `generated_file_path` below OR prompt user to choose file.
-- 2) Run script from ReaScript.

local generated_file_path = ""

if generated_file_path == "" then
  retval, selected = reaper.GetUserFileNameForRead("", "Select generated audio file", ".wav")
  if not retval then return end
  generated_file_path = selected
end

if not reaper.file_exists(generated_file_path) then
  reaper.ShowMessageBox("Generated file not found:\n" .. generated_file_path, "Suno Studio Bridge", 0)
  return
end

reaper.Undo_BeginBlock()
local cursor = reaper.GetCursorPosition()
reaper.SetEditCurPos(cursor, false, false)
reaper.InsertMedia(generated_file_path, 0)
reaper.Undo_EndBlock("Insert generated file at edit cursor", -1)
reaper.UpdateArrange()
