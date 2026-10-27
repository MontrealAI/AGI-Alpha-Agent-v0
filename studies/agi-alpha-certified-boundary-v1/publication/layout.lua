-- SPDX-License-Identifier: Apache-2.0
-- Keep short mathematical lead-ins with their displays in the print edition.
function Pandoc(doc)
  if not FORMAT:match('latex') then return doc end
  local result = pandoc.List()
  local i = 1
  while i <= #doc.blocks do
    local current = doc.blocks[i]
    local following = doc.blocks[i + 1]
    if current.t == 'Header' and current.level == 1 and
       pandoc.utils.stringify(current):match('^Appendix A%.') then
      result:insert(pandoc.RawBlock('latex', '\\clearpage'))
    end
    if current.t == 'Header' and current.level == 1 then
      result:insert(pandoc.RawBlock('latex', '\\Needspace{9\\baselineskip}'))
    end
    if current.t == 'Header' and current.level == 2 then
      result:insert(pandoc.RawBlock('latex', '\\Needspace{7\\baselineskip}'))
    end
    local display = following and following.t == 'Para' and #following.content == 1 and
                    following.content[1].t == 'Math' and following.content[1].mathtype == 'DisplayMath'
    local has_display = false
    if current.t == 'Para' then
      for _, inline in ipairs(current.content) do
        if inline.t == 'Math' and inline.mathtype == 'DisplayMath' then has_display = true end
      end
    end
    if current.t == 'Para' and has_display and #pandoc.utils.stringify(current) < 1000 then
      result:insert(pandoc.RawBlock('latex', '\\begin{samepage}'))
      result:insert(current)
      result:insert(pandoc.RawBlock('latex', '\\end{samepage}'))
      i = i + 1
    elseif current.t == 'Para' and display and #pandoc.utils.stringify(current) < 400 then
      result:insert(pandoc.RawBlock('latex', '\\begin{samepage}'))
      result:insert(current)
      result:insert(following)
      result:insert(pandoc.RawBlock('latex', '\\end{samepage}'))
      i = i + 2
    else
      result:insert(current)
      i = i + 1
    end
  end
  doc.blocks = result
  return doc
end
