import 'package:flutter/material.dart';
import 'colors.dart';

class NeobrutalCard extends StatelessWidget {
  final Widget child;
  final Color? backgroundColor;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final VoidCallback? onTap;
  final double shadowOffset;
  final Color? borderColor;

  const NeobrutalCard({
    super.key,
    required this.child,
    this.backgroundColor,
    this.padding = const EdgeInsets.all(16.0),
    this.margin,
    this.onTap,
    this.shadowOffset = AppColors.shadowOffset,
    this.borderColor,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = borderColor ?? (isDark ? AppColors.darkInk : AppColors.ink);
    final bgColor = backgroundColor ?? (isDark ? AppColors.darkSurface : AppColors.surface);

    Widget card = Container(
      margin: margin,
      decoration: BoxDecoration(
        color: bgColor,
        border: Border.all(color: inkColor, width: AppColors.borderWidth),
        boxShadow: [
          if (shadowOffset > 0)
            BoxShadow(
              color: inkColor,
              offset: Offset(shadowOffset, shadowOffset),
              blurRadius: 0,
            ),
        ],
      ),
      padding: padding,
      child: child,
    );

    if (onTap != null) {
      return GestureDetector(
        onTap: onTap,
        child: card,
      );
    }
    return card;
  }
}

class NeobrutalButton extends StatefulWidget {
  final String text;
  final VoidCallback? onPressed;
  final Color? backgroundColor;
  final Color? textColor;
  final IconData? icon;
  final bool isFullWidth;
  final double height;
  final bool isLoading;

  const NeobrutalButton({
    super.key,
    required this.text,
    required this.onPressed,
    this.backgroundColor,
    this.textColor,
    this.icon,
    this.isFullWidth = true,
    this.height = 50.0,
    this.isLoading = false,
  });

  @override
  State<NeobrutalButton> createState() => _NeobrutalButtonState();
}

class _NeobrutalButtonState extends State<NeobrutalButton> {
  bool _isPressed = false;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;
    final bgColor = widget.backgroundColor ?? AppColors.action;
    final txtColor = widget.textColor ?? Colors.black;

    final double currentOffset = _isPressed ? 1.0 : AppColors.shadowOffset;
    final double translation = _isPressed ? (AppColors.shadowOffset - 1.0) : 0.0;

    return GestureDetector(
      onTapDown: widget.onPressed == null || widget.isLoading
          ? null
          : (_) => setState(() => _isPressed = true),
      onTapUp: widget.onPressed == null || widget.isLoading
          ? null
          : (_) {
              setState(() => _isPressed = false);
              widget.onPressed?.call();
            },
      onTapCancel: () => setState(() => _isPressed = false),
      child: Transform.translate(
        offset: Offset(translation, translation),
        child: Container(
          width: widget.isFullWidth ? double.infinity : null,
          height: widget.height,
          padding: const EdgeInsets.symmetric(horizontal: 20.0),
          decoration: BoxDecoration(
            color: widget.onPressed == null ? Colors.grey.shade400 : bgColor,
            border: Border.all(color: inkColor, width: AppColors.borderWidth),
            boxShadow: [
              if (currentOffset > 0 && widget.onPressed != null)
                BoxShadow(
                  color: inkColor,
                  offset: Offset(currentOffset, currentOffset),
                  blurRadius: 0,
                ),
            ],
          ),
          child: Center(
            child: widget.isLoading
                ? const SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(
                      strokeWidth: 3,
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.black),
                    ),
                  )
                : Row(
                    mainAxisSize: MainAxisSize.min,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      if (widget.icon != null) ...[
                        Icon(widget.icon, color: txtColor, size: 20),
                        const SizedBox(width: 8),
                      ],
                      Text(
                        widget.text,
                        style: TextStyle(
                          color: txtColor,
                          fontWeight: FontWeight.w800,
                          fontSize: 16,
                          letterSpacing: 0.2,
                        ),
                      ),
                    ],
                  ),
          ),
        ),
      ),
    );
  }
}

class NeobrutalBadge extends StatelessWidget {
  final String label;
  final Color backgroundColor;
  final Color? textColor;
  final IconData? icon;

  const NeobrutalBadge({
    super.key,
    required this.label,
    required this.backgroundColor,
    this.textColor = Colors.black,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: backgroundColor,
        border: Border.all(color: inkColor, width: 2.0),
        boxShadow: [
          BoxShadow(
            color: inkColor,
            offset: const Offset(2, 2),
            blurRadius: 0,
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 14, color: textColor),
            const SizedBox(width: 4),
          ],
          Text(
            label,
            style: TextStyle(
              color: textColor,
              fontWeight: FontWeight.w700,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }
}

class NeobrutalTextField extends StatelessWidget {
  final TextEditingController controller;
  final String label;
  final String? hint;
  final TextInputType? keyboardType;
  final bool obscureText;
  final String? Function(String?)? validator;
  final int maxLines;
  final Widget? prefix;
  final Widget? suffix;

  const NeobrutalTextField({
    super.key,
    required this.controller,
    required this.label,
    this.hint,
    this.keyboardType,
    this.obscureText = false,
    this.validator,
    this.maxLines = 1,
    this.prefix,
    this.suffix,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;
    final bgColor = isDark ? AppColors.darkSurface : AppColors.surface;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label.toUpperCase(),
          style: TextStyle(
            fontWeight: FontWeight.w800,
            fontSize: 12,
            letterSpacing: 0.8,
            color: isDark ? AppColors.darkInk : AppColors.ink,
          ),
        ),
        const SizedBox(height: 6),
        Container(
          decoration: BoxDecoration(
            color: bgColor,
            border: Border.all(color: inkColor, width: AppColors.borderWidth),
            boxShadow: [
              BoxShadow(
                color: inkColor,
                offset: const Offset(AppColors.shadowOffset, AppColors.shadowOffset),
                blurRadius: 0,
              ),
            ],
          ),
          child: TextFormField(
            controller: controller,
            keyboardType: keyboardType,
            obscureText: obscureText,
            validator: validator,
            maxLines: maxLines,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: isDark ? AppColors.darkInk : AppColors.ink,
            ),
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: TextStyle(
                color: isDark ? AppColors.darkMuted : AppColors.muted,
                fontWeight: FontWeight.w400,
              ),
              border: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              prefixIcon: prefix,
              suffixIcon: suffix,
            ),
          ),
        ),
        const SizedBox(height: 16),
      ],
    );
  }
}

class MoneyText extends StatelessWidget {
  final String amount;
  final double fontSize;
  final FontWeight fontWeight;
  final Color? color;

  const MoneyText({
    super.key,
    required this.amount,
    this.fontSize = 18,
    this.fontWeight = FontWeight.w700,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final defaultColor = isDark ? AppColors.darkInk : AppColors.ink;

    String cleanAmount = amount.replaceAll('₹', '').trim();

    return Text(
      '₹$cleanAmount',
      style: TextStyle(
        fontFamily: 'monospace',
        fontSize: fontSize,
        fontWeight: fontWeight,
        color: color ?? defaultColor,
      ),
    );
  }
}

class CategoryDot extends StatelessWidget {
  final Color color;
  final double size;

  const CategoryDot({
    super.key,
    required this.color,
    this.size = 14.0,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: color,
        border: Border.all(color: inkColor, width: AppColors.thinBorderWidth),
      ),
    );
  }
}

class AvatarChipWidget extends StatelessWidget {
  final String initials;
  final VoidCallback? onTap;
  final double size;

  const AvatarChipWidget({
    super.key,
    required this.initials,
    this.onTap,
    this.size = 38.0,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    Widget chip = Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkSurface : AppColors.surface,
        border: Border.all(color: inkColor, width: AppColors.thinBorderWidth),
        boxShadow: [
          BoxShadow(
            color: inkColor,
            offset: const Offset(AppColors.smallShadowOffset, AppColors.smallShadowOffset),
            blurRadius: 0,
          ),
        ],
      ),
      child: Center(
        child: Text(
          initials.toUpperCase(),
          style: TextStyle(
            fontFamily: 'monospace',
            fontWeight: FontWeight.w900,
            fontSize: size * 0.38,
            color: isDark ? AppColors.darkInk : AppColors.ink,
          ),
        ),
      ),
    );

    if (onTap != null) {
      return GestureDetector(onTap: onTap, child: chip);
    }
    return chip;
  }
}

class DottedLeaderLine extends StatelessWidget {
  const DottedLeaderLine({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = (isDark ? AppColors.darkInk : AppColors.ink).withValues(alpha: 0.35);

    return LayoutBuilder(
      builder: (context, constraints) {
        final boxWidth = constraints.constrainWidth();
        if (boxWidth < 12) return const SizedBox.shrink();
        const dotSize = 3.0;
        const gap = 4.0;
        final count = (boxWidth / (dotSize + gap)).floor();
        return Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: List.generate(count, (_) {
            return Container(
              width: dotSize,
              height: dotSize,
              color: inkColor,
            );
          }),
        );
      },
    );
  }
}

class NeobrutalLedgerRow extends StatelessWidget {
  final Widget? leading;
  final String title;
  final String? subtitle;
  final String? amount;
  final Color? amountColor;
  final Widget? trailing;
  final VoidCallback? onTap;
  final bool showBottomBorder;

  const NeobrutalLedgerRow({
    super.key,
    this.leading,
    required this.title,
    this.subtitle,
    this.amount,
    this.amountColor,
    this.trailing,
    this.onTap,
    this.showBottomBorder = true,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    Widget content = Container(
      padding: const EdgeInsets.symmetric(vertical: 11.0),
      decoration: BoxDecoration(
        border: showBottomBorder
            ? Border(
                bottom: BorderSide(
                  color: inkColor,
                  width: AppColors.thinBorderWidth,
                ),
              )
            : null,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          if (leading != null) ...[
            leading!,
            const SizedBox(width: 10),
          ],
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 15,
                    color: isDark ? AppColors.darkInk : AppColors.ink,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                if (subtitle != null && subtitle!.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(
                    subtitle!,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: isDark ? AppColors.darkMuted : AppColors.muted,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 8),
          const Expanded(
            flex: 0,
            child: SizedBox(
              width: 32,
              child: DottedLeaderLine(),
            ),
          ),
          const SizedBox(width: 8),
          if (amount != null)
            MoneyText(
              amount: amount!,
              fontSize: 15,
              fontWeight: FontWeight.w800,
              color: amountColor ?? (isDark ? AppColors.darkInk : AppColors.ink),
            ),
          if (trailing != null) ...[
            const SizedBox(width: 8),
            trailing!,
          ],
        ],
      ),
    );

    if (onTap != null) {
      return InkWell(onTap: onTap, child: content);
    }
    return content;
  }
}
