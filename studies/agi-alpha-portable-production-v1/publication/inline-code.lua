-- SPDX-License-Identifier: Apache-2.0
-- Allow long frozen identities and evidence paths to break inside the measure.
function Code(el)
  if FORMAT == "latex" then
    return pandoc.RawInline("latex", "\\nolinkurl{" .. el.text .. "}")
  end
end

function Table(el)
  if FORMAT ~= "latex" then return end
  local n = #el.colspecs
  local widths
  local cells = el.head.rows[1].cells
  local first = pandoc.utils.stringify(cells[1].contents)
  local second = pandoc.utils.stringify(cells[2].contents)
  if n == 2 then
    widths = {.70,.30}
  elseif n == 3 then
    if second == "Result" or second == "USD" then
      widths = {.40,.15,.45}
    elseif first == "Claim" then
      widths = {.27,.31,.42}
    else
      widths = {.25,.37,.38}
    end
  elseif n == 4 then
    widths = {.34,.23,.23,.20}
  end
  if widths then
    for i, width in ipairs(widths) do
      el.colspecs[i] = {el.colspecs[i][1],width}
    end
  end
  if n == 4 then
    return {pandoc.RawBlock("latex", "\\Needspace{220pt}"), el}
  end
  return el
end
