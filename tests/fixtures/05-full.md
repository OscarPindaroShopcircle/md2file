# Full feature showcase

This document exercises **every** supported feature so we can eyeball the whole
rendering surface in one place.

## Text and inline

A paragraph with **bold**, *italic*, `inline code`, and a
[link](https://example.com). Soft
breaks inside a paragraph collapse to spaces.

### A third-level heading

Body text under an `h3`.

## Lists

- Unordered one
- Unordered two
  - Nested two-a
  - Nested two-b
- Unordered three

1. Ordered one
2. Ordered two
3. Ordered three

## Table

| Component | Owner    | Done |
|:----------|:--------:|-----:|
| Parser    | Alice    | Yes  |
| Renderer  | Bob      | No   |

## Code

```js
function greet(name) {
  return `hello, ${name}`;
}
```

## Blockquote

> This is a blockquote. It should be indented with a colored left border and
> rendered in a muted tone.

## Divider

---

## Image

![sample image](assets/sample.png)

End of showcase.
