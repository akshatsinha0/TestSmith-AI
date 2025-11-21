# QA Strategy: E-Shop Checkout

This document describes the key viewpoints that the autonomous QA agent should cover when generating test cases.

## Functional Viewpoints
- Discount logic
  - Validate that SAVE15 applies a 15% discount to the subtotal.
  - Validate that unknown codes do not apply any discount.
- Shipping selection
  - Standard shipping is free.
  - Express shipping adds $10 to the total.
- Form validation
  - All required fields must be validated before payment.
  - Inline error messages must appear in red.

## Negative Viewpoints
- Invalid email formats.
- Empty required fields.
- Applying SAVE15 when the cart is empty.

## Boundary Viewpoints
- Maximum supported quantity for a single item line.
- Applying SAVE15 when subtotal is exactly at a documented threshold (if any).

The agent should produce a balanced set of positive, negative, and boundary tests across these viewpoints.