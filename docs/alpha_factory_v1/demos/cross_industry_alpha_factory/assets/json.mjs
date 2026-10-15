export function parseJSON(text, integerOnly = true) {
    if (new TextEncoder().encode(text).length > 1048576)
        throw new Error("Fixture exceeds 1 MiB");
    let at = 0;
    const ws = () => {
        while (/[\t\n\r ]/.test(text[at] || "\0")) at++;
    };
    const fail = () => {
        throw new Error("Invalid JSON or noninteger numeric token");
    };
    function string() {
        const start = at++;
        while (at < text.length) {
            if (text[at] === "\\") {
                at += 2;
                continue;
            }
            if (text[at++] === '"') return JSON.parse(text.slice(start, at));
        }
        fail();
    }
    function value(depth = 0) {
        if (depth > 32) throw new Error("Input nesting is too deep");
        ws();
        const c = text[at];
        if (c === '"') return string();
        if (c === "{") {
            at++;
            ws();
            const obj = Object.create(null),
                seen = new Set();
            if (text[at] === "}") {
                at++;
                return obj;
            }
            while (true) {
                ws();
                if (text[at] !== '"') fail();
                const key = string();
                if (seen.has(key)) throw new Error("Duplicate JSON key");
                seen.add(key);
                ws();
                if (text[at++] !== ":") fail();
                obj[key] = value(depth + 1);
                ws();
                const sep = text[at++];
                if (sep === "}") return obj;
                if (sep !== ",") fail();
            }
        }
        if (c === "[") {
            at++;
            ws();
            const arr = [];
            if (text[at] === "]") {
                at++;
                return arr;
            }
            while (true) {
                arr.push(value(depth + 1));
                ws();
                const sep = text[at++];
                if (sep === "]") return arr;
                if (sep !== ",") fail();
            }
        }
        for (const [token, result] of [
            ["true", true],
            ["false", false],
            ["null", null],
        ])
            if (text.startsWith(token, at)) {
                at += token.length;
                return result;
            }
        const token = text
            .slice(at)
            .match(
                integerOnly
                    ? /^-?(?:0|[1-9][0-9]*)/
                    : /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/
            );
        if (!token) fail();
        at += token[0].length;
        if (/[.eE0-9]/.test(text[at] || "\0")) fail();
        const number = Number(token[0]);
        if (!Number.isFinite(number)) fail();
        return number;
    }
    const parsed = value();
    ws();
    if (at !== text.length) fail();
    return parsed;
}
