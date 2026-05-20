# Products Folder Structure

Each subfolder represents one product to be listed. The folder name is used as an identifier.

## Expected Layout

```
products/
  product-001/
    product.json
    images/
      01.jpg
      02.jpg
      03.jpg
  product-002/
    product.json
    images/
      01.jpg
      02.png
```

## product.json Fields

| Field       | Type   | Required | Description                        |
|-------------|--------|----------|------------------------------------|
| title       | string | Yes      | Product title for the listing      |
| description | string | Yes      | Product description (HTML allowed) |
| sku         | string | Yes      | Unique SKU identifier              |
| price       | number | Yes      | Product price                      |
| category    | string | No       | Product category path              |

## Image Requirements

- Supported formats: .jpg, .jpeg, .png, .gif, .webp
- Images are uploaded in alphabetical order by filename
- Recommended naming: 01.jpg, 02.jpg, 03.jpg, etc.
- First image will be used as the main product image
