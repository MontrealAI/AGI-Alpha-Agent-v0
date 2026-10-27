-- SPDX-License-Identifier: Apache-2.0
-- Allow artifact paths to break at safe separators in the LaTeX reader.
function Code(element)
  if FORMAT:match('latex') and element.text:match('^[%w_./%-]+$') and element.text:find('/') then
    return pandoc.RawInline('latex', '\\path{' .. element.text .. '}')
  end
end
