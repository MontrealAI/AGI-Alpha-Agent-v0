function HorizontalRule()
  return pandoc.RawBlock('latex', '\\clearpage')
end

function Code(el)
  return pandoc.RawInline('latex', '\\path{' .. el.text .. '}')
end
