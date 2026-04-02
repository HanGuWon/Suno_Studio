-- export_time_selection_to_file.lua
-- Minimal proof-of-concept export path.
-- Prefers time selection. Falls back to selected item bounds.

local function get_export_range()
  local start_time, end_time = reaper.GetSet_LoopTimeRange(false, false, 0, 0, false)
  if end_time > start_time then
    return start_time, end_time
  end

  local item = reaper.GetSelectedMediaItem(0, 0)
  if item ~= nil then
    local pos = reaper.GetMediaItemInfo_Value(item, "D_POSITION")
    local len = reaper.GetMediaItemInfo_Value(item, "D_LENGTH")
    return pos, pos + len
  end

  return nil, nil
end

local start_time, end_time = get_export_range()
if not start_time then
  reaper.ShowMessageBox("No time selection or selected media item found.", "Suno Studio Bridge", 0)
  return
end

retval, output_path = reaper.GetUserFileNameForRead("", "Choose export output path (type .wav filename)", ".wav")
if not retval then return end

-- This PoC sets render bounds; user still triggers render manually (honest minimal path).
reaper.GetSet_LoopTimeRange(true, false, start_time, end_time, false)
reaper.ShowConsoleMsg("Suno Studio Bridge PoC:\n")
reaper.ShowConsoleMsg("Render range prepared: " .. tostring(start_time) .. " - " .. tostring(end_time) .. "\n")
reaper.ShowConsoleMsg("Output path chosen: " .. output_path .. "\n")
reaper.ShowConsoleMsg("Next step: run REAPER Render using Time Selection + WAV to this path.\n")
